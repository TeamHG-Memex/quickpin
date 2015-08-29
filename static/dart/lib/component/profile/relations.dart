import 'dart:async';

import 'package:angular/angular.dart';
import 'package:quickpin/component/breadcrumbs.dart';
import 'package:quickpin/component/pager.dart';
import 'package:quickpin/component/title.dart';
import 'package:quickpin/mixin/current_page.dart';
import 'package:quickpin/model/profile.dart';
import 'package:quickpin/rest_api.dart';

/// A component for posts by a specified profile.
@Component(
    selector: 'profile-relations',
    templateUrl: 'packages/quickpin/component/profile/relations.html',
    useShadowDom: false
)
class ProfileRelationsComponent extends Object with CurrentPageMixin
                                implements ScopeAware {
    List<Breadcrumb> crumbs;
    String error = '';
    String id;
    int loading = 0;
    Pager pager;
    List<Profile> relations;
    Scope scope;
    String siteName;
    String username;

    String _relType;

    final RestApiController api;
    final RouteProvider _rp;
    final int _resultsPerPage = 30;
    final TitleService _ts;

    /// Constructor.
    ProfileRelationsComponent(this.api, this._rp, this._ts) {
        this.initCurrentPage(this._rp.route, this._fetchCurrentPage);
        this.id = this._rp.parameters['id'];
        this._relType = this._rp.parameters['reltype'];
        this._ts.title = 'Posts by ${id}';
        this._updateCrumbs();
        this._fetchCurrentPage();
    }

    /// Return relation type as a human-readable string.
    String relType({bool uppercase: false}) {
        String relType;

        if (this._relType == 'friends') {
            relType = 'friends';
        } else {
            relType = 'followers';
        }

        if (uppercase) {
            relType = relType.replaceRange(0, 1, relType[0].toUpperCase());
        }

        return relType;
    }

    /// Fetch list of relations.
    void _fetchCurrentPage() {
        this.error = '';
        this.loading++;
        String pageUrl = '/api/profile/${this.id}/relations/${this._relType}';
        Map urlArgs = {
            'page': this.currentPage,
            'rpp': this._resultsPerPage,
        };

        this.api
            .get(pageUrl, urlArgs: urlArgs, needsAuth: true)
            .then((response) {
                this.siteName = response.data['site_name'];
                this.username = response.data['username'];
                this.relations = new List<Profile>();

                response.data['relations'].forEach((relation) {
                    this.relations.add(new Profile.fromJson(relation));
                });

                this.pager = new Pager(response.data['total_count'],
                                       this.currentPage,
                                       resultsPerPage:this._resultsPerPage);

                this._ts.title = '${this.relType()} by ${this.username}';
                this._updateCrumbs();

                new Future(() {
                    this.scope.broadcast('masonry.layout');
                });
            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {this.loading--;});
    }

    /// Update breadcrumbs.
    void _updateCrumbs() {
        String username;

        if (this.username == null) {
            username = this.id;
        } else {
            username = this.username;
        }

        this.crumbs = [
            new Breadcrumb('QuickPin', '/'),
            new Breadcrumb('Profiles', '/profile'),
            new Breadcrumb(this.username, '/profile/${this.id}'),
            new Breadcrumb(this.relType()),
        ];
    }
}
