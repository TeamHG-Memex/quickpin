import 'dart:async';
import 'dart:html';
import 'dart:math';

import 'package:angular/angular.dart';
import 'package:quickpin/authentication.dart';
import 'package:quickpin/component/breadcrumbs.dart';
import 'package:quickpin/component/title.dart';
import 'package:quickpin/mixin/current_page.dart';
import 'package:quickpin/model/profile.dart';
import 'package:quickpin/rest_api.dart';

/// A component for listing profiles.
@Component(
    selector: 'profile-list',
    templateUrl: 'packages/quickpin/component/profile/list.html',
    useShadowDom: false
)
class ProfileListComponent extends Object with CurrentPageMixin
                           implements ShadowRootAware {
    List<Breadcrumb> crumbs = [
        new Breadcrumb('QuickPin', '/'),
        new Breadcrumb('Profiles'),
    ];

    String error;
    bool loading = false;
    String newProfile;
    List<Profile> profiles;
    bool showAdd = true;
    bool submittingProfile = false;

    InputElement _inputEl;

    final AuthenticationController auth;
    final RestApiController _api;
    final Element _element;
    final int _resultsPerPage = 10;
    final Router _router;
    final RouteProvider _rp;
    final TitleService _ts;

    /// Constructor.
    ProfileListComponent(this.auth, this._api, this._element, this._router,
                         this._rp, this._ts) {
        this._fetchCurrentPage();
        this._ts.title = 'Profiles';
    }

    /// Submit a new profile.
    void addProfile() {
        this.error = null;
        this.submittingProfile = true;
        String pageUrl = '/api/profile/';
        Map body = {'profiles': [{'name': this.newProfile, 'site': 'twitter'}]};
        this.profiles.insert(0, new Profile(this.newProfile, 'twitter'));

        this._api
            .post(pageUrl, body, needsAuth: true)
            .then((response) {
                this.newProfile = '';
                new Timer(new Duration(seconds:0.1), () => this._inputEl.focus());
            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {this.submittingProfile = false;});
    }

    /// Trigger add profile when the user presses enter in the profile input.
    void handleAddProfileKeypress(Event e) {
        if (e.charCode == 13) {
            addProfile();
        }
    }

    /// Show the "add profile" dialog.
    void hideAddDialog() {
        this.showAdd = false;
        this.newProfile = '';
    }

    /// Get a reference to this element.
    void onShadowRoot(ShadowRoot shadowRoot) {
        this._inputEl = this._element.querySelector('.add-profile-form input');
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

    /// Fetch a page of profiles.
    void _fetchCurrentPage() {
        this.error = null;
        this.loading = true;
        String pageUrl = '/api/profile/';

        this._api
            .get(pageUrl, needsAuth: true)
            .then((response) {
                this.profiles = new List.generate(
                    response.data['profiles'].length,
                    (index) => new Profile.fromJson(response.data['profiles'][index])
                );
            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {this.loading = false;});
    }
}
