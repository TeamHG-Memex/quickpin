import 'dart:async';
import 'dart:convert';
import 'dart:html';

import 'package:angular/angular.dart';
import 'package:quickpin/authentication.dart';
import 'package:quickpin/component/breadcrumbs.dart';
import 'package:quickpin/component/pager.dart';
import 'package:quickpin/component/title.dart';
import 'package:quickpin/mixin/current_page.dart';
import 'package:quickpin/model/label.dart';
import 'package:quickpin/rest_api.dart';
import 'package:quickpin/sse.dart';

/// A component for listing profiles.
@Component(
    selector: 'label-list',
    templateUrl: 'packages/quickpin/component/label/list.html',
    useShadowDom: false
)
class LabelListComponent extends Object with CurrentPageMixin
                           implements ScopeAware, ShadowRootAware {
    List<Breadcrumb> crumbs = [
        new Breadcrumb('QuickPin', '/'),
        new Breadcrumb('Labels'),
    ];

    String error;
    String id;
    int loading = 0;
    String newLabel;
    List<String> labelIds;
    Map<String,Function> labels;
    Pager pager;
    Scope scope;
    bool showAdd = false;
    bool submittingLabel = false;
    bool labelCreated = false;

    InputElement _inputEl;

    final RestApiController api;
    final AuthenticationController auth;
    final Element _element;
    final Router _router;
    final RouteProvider _rp;
    final int _resultsPerPage = 5;
    final SseController _sse;
    final TitleService _ts;

    /// Constructor.
    LabelListComponent(this.api, this.auth, this._element, this._router,
                         this._rp, this._sse, this._ts) {
        this.initCurrentPage(this._rp.route, this._fetchCurrentPage);
        this._ts.title = 'Labels';
        this.id = this._rp.parameters['id'];

        // Add event listeners...
        RouteHandle rh = this._rp.route.newHandle();

        List<StreamSubscription> listeners = [
            this._sse.onLabel.listen(this.labelListener),
            //this._sse.onLabel.listen(this._fetchCurrentPage()),
            rh.onEnter.listen((e) {
                this._fetchCurrentPage();
            }),
        ];

        // ...and remove event listeners when we leave this route.
        rh.onLeave.take(1).listen((e) {
            listeners.forEach((listener) => listener.cancel());
        });

        this._fetchCurrentPage();
    }

    /// Submit a new label.
    void addLabel() {
        String pageUrl = '/api/label/';
        this.error = null;
        this.submittingLabel = true;
        this.loading++;

        Map body = {
            'labels': [{
                'name': this.newLabel,
            }],
        };

        this.api
            .post(pageUrl, body, needsAuth: true)
            .then((response) {
                this.labelCreated = true;
                new Timer(new Duration(seconds:0.1), () => this._inputEl.focus());
                new Timer(new Duration(seconds:2), () {
                    this.labelCreated = false;
                    this.newLabel = '';
                });
                new Future(() {
                    this.scope.broadcast('masonry.layout');
                });
            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {
                this.submittingLabel = false;
                this.loading--;
            });
    }

    /// Save an edited label.
    void saveLabel(String id_, String name) {
        String pageUrl = '/api/label/${id_}';
        this.error = null;
        this.loading++;

        Map body = {
            'name': name,
        };

        this.api
            .put(pageUrl, body, needsAuth: true)
            .then((response) {
                this.labels[id_]['name'] = name;

                new Future(() {
                    this.scope.broadcast('masonry.layout');
                });
            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {
                this.loading--;
            });
    }

    /// Trigger add label when the user presses enter in the label input.
    void handleAddLabelKeypress(Event e) {
        if (e.charCode == 13) {
            addLabel();
        }
    }

    /// Show the "add profile" dialog.
    void hideAddDialog() {
        this.showAdd = false;
        this.newLabel = '';
    }

    /// Get a reference to this element.
    void onShadowRoot(ShadowRoot shadowRoot) {
        this._inputEl = this._element.querySelector('.add-label-form input');
    }

    /// Show the "add profile" dialog.
    void showAddDialog() {
        this.showAdd = true;

        if (this._inputEl != null) {
            // Allow Angular to digest showAdd before trying to focus. (Can't
            // focus a hidden element.)
            new Timer(new Duration(seconds:0.1), () => this._inputEl.focus());
        }
    }

    Future _fetchCurrentPage() {
        Completer completer = new Completer();
        this.error = null;
        this.loading++;
        String pageUrl = '/api/label/';
        Map urlArgs = {
            'page': this.currentPage,
            'rpp': this._resultsPerPage,
        };

        this.api
            .get(pageUrl, urlArgs: urlArgs, needsAuth: true)
            .then((response) {
                this.labels = new Map<String>();
                this.labelIds = new List<String>();

                response.data['labels'].forEach((label) {
                    this.labels[label['id']] = {
                        'name': label['name'],
                        'save': (v) => this.saveLabel(label['id'], v),
                    };
                });

                this.pager = new Pager(response.data['total_count'],
                                       this.currentPage,
                                       resultsPerPage:this._resultsPerPage);

                new Future(() {
                    this.labelIds = new List<String>.from(this.labels.keys);
                    this.scope.broadcast('masonry.layout');
                });
            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {
                this.loading--;
                completer.complete();
            });

       return completer.future;
    }

    /// Listen for label updates.
    void labelListener(Event e) {
        Map json = JSON.decode(e.data);

        if (json['error'] == null) {
            this._fetchCurrentPage();
        } 
    }
}
