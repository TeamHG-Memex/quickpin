import 'dart:async';
import 'dart:html';
import 'dart:js';

import 'package:angular/angular.dart';
import 'package:quickpin/authentication.dart';
import 'package:quickpin/component/breadcrumbs.dart';
import 'package:quickpin/component/title.dart';
import 'package:quickpin/model/post.dart';
import 'package:quickpin/model/profile.dart';
import 'package:quickpin/rest_api.dart';
import 'package:bootjack/bootjack.dart';
import 'package:dquery/dquery.dart';

/// A controller for viewing and editing a profile.
@Component(
    selector: 'profile',
    templateUrl: 'packages/quickpin/component/profile/view.html',
    useShadowDom: false
)
class ProfileComponent {
    AuthenticationController auth;
    List<Breadcrumb> crumbs;
    List<Profile> followers;
    List<Profile> friends;
    int id;
    int loading = 0;
    List<Post> posts;
    Profile profile;

    final RestApiController _api;
    final RouteProvider _rp;
    final TitleService _ts;

    /// Constructor.
    ProfileComponent(this.auth, this._api, this._rp, this._ts) {
        String idParam = Uri.decodeComponent(this._rp.parameters['id']);
        this.id = int.parse(idParam, radix:10);

        this.crumbs = [
            new Breadcrumb('QuickPin', '/'),
            new Breadcrumb('Profiles', '/profile'),
            new Breadcrumb(this.id.toString()),
        ];

        this._fetchProfile()
            .then((_) => this._fetchPosts())
            .then((_) => this._fetchFriends())
            .then((_) => this._fetchFollowers());
    }

    /// Return a URL for a profile's avatar image.
    String avatarUrl(profile) {
        if (profile.avatarUrls.length > 0) {
            return profile.avatarUrls[0] +
                   '?xauth=' +
                   Uri.encodeFull(this.auth.token);
        } else {
            return '/static/img/default_user_thumb_large.png';
        }
    }

    /// Fetch a page of followers for this profile.
    Future _fetchFollowers() {
        Completer completer = new Completer();
        this.loading++;
        String url = '/api/profile/${this.id}/followers';
        Map urlArgs = {'page': 1, 'rpp': 10};

        this._api
            .get(url, urlArgs: urlArgs, needsAuth: true)
            .then((response) {
                List followers = response.data['followers'];
                this.followers = new List<Post>.generate(followers.length, (index) {
                    return new Profile.fromJson(followers[index]);
                });
            })
            .whenComplete(() {
                this.loading--;
                completer.complete();
            });

        return completer.future;
    }

    /// Fetch a page of friends for this profile.
    Future _fetchFriends() {
        Completer completer = new Completer();
        this.loading++;
        String url = '/api/profile/${this.id}/friends';
        Map urlArgs = {'page': 1, 'rpp': 10};

        this._api
            .get(url, urlArgs: urlArgs, needsAuth: true)
            .then((response) {
                List friends = response.data['friends'];
                this.friends = new List<Post>.generate(friends.length, (index) {
                    return new Profile.fromJson(friends[index]);
                });
            })
            .whenComplete(() {
                this.loading--;
                completer.complete();
            });

        return completer.future;
    }

    /// Fetch recent posts for this profile.
    Future _fetchPosts() {
        Completer completer = new Completer();
        this.loading++;
        String url = '/api/profile/${this.id}/posts';
        Map urlArgs = {'page': 1, 'rpp': 8};

        this._api
            .get(url, urlArgs: urlArgs, needsAuth: true)
            .then((response) {
                List jsonPosts = response.data['posts'];
                this.posts = new List<Post>.generate(jsonPosts.length, (index) {
                    return new Post.fromJson(jsonPosts[index]);
                });
            })
            .whenComplete(() {
                this.loading--;
                completer.complete();
            });

        return completer.future;
    }

    /// Fetch data about this profile.
    Future _fetchProfile() {
        Completer completer = new Completer();
        this.loading++;

        this._api
            .get('/api/profile/${this.id}', needsAuth: true)
            .then((response) {
                this.profile = new Profile.fromJson(response.data);
                this.crumbs[this.crumbs.length-1] = new Breadcrumb(this.profile.username);
                this._ts.title = this.profile.username;
            })
            .whenComplete(() {
                this.loading--;
                completer.complete();
            });

        return completer.future;
    }
}
