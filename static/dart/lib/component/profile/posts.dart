import 'dart:async';

import 'package:angular/angular.dart';
import 'package:quickpin/component/breadcrumbs.dart';
import 'package:quickpin/component/pager.dart';
import 'package:quickpin/component/title.dart';
import 'package:quickpin/mixin/current_page.dart';
import 'package:quickpin/model/post.dart';
import 'package:quickpin/rest_api.dart';

/// A component for posts by a specified profile.
@Component(
    selector: 'profile-posts',
    templateUrl: 'packages/quickpin/component/profile/posts.html',
    useShadowDom: false
)
class ProfilePostsComponent extends Object with CurrentPageMixin
                            implements ScopeAware {
    List<Breadcrumb> crumbs;

    String error = '';
    String id;
    int loading = 0;
    Pager pager;
    List<Post> posts;
    Scope scope;
    String siteName;
    String username;

    final RestApiController _api;
    final RouteProvider _rp;
    final int _resultsPerPage = 20;
    final TitleService _ts;

    /// Constructor.
    ProfilePostsComponent(this._api, this._rp, this._ts) {
        this.initCurrentPage(this._rp.route, this._fetchCurrentPage);
        this.id = this._rp.parameters['id'];
        this._ts.title = 'Posts by ${id}';
        this._updateCrumbs();
        this._fetchCurrentPage();
    }

    /// Fetch list of posts.
    void _fetchCurrentPage() {
        this.error = '';
        this.loading++;
        String pageUrl = '/api/profile/${this.id}/posts';
        Map urlArgs = {
            'page': this.currentPage,
            'rpp': this._resultsPerPage,
        };

        this._api
            .get(pageUrl, urlArgs: urlArgs, needsAuth: true)
            .then((response) {
                this.siteName = response.data['site_name'];
                this.username = response.data['username'];
                this.posts = new List<Post>();

                response.data['posts'].forEach((post) {
                    this.posts.add(new Post.fromJson(post));
                });

                this.pager = new Pager(response.data['total_count'],
                                       this.currentPage,
                                       resultsPerPage:this._resultsPerPage);

                this._ts.title = 'Posts by ${this.username}';
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
            new Breadcrumb('Posts'),
        ];
    }
}
