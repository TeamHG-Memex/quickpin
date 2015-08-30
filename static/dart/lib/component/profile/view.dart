import 'dart:async';
import 'dart:convert';
import 'dart:html';
import 'dart:js';

import 'package:angular/angular.dart';
import 'package:quickpin/authentication.dart';
import 'package:quickpin/component/breadcrumbs.dart';
import 'package:quickpin/component/title.dart';
import 'package:quickpin/model/post.dart';
import 'package:quickpin/model/profile.dart';
import 'package:quickpin/rest_api.dart';
import 'package:quickpin/sse.dart';
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

    final RestApiController api;
    final RouteProvider _rp;
    final SseController _sse;
    final TitleService _ts;

    /// Constructor.
    ProfileComponent(this.api, this.auth, this._rp, this._sse, this._ts) {
        String idParam = Uri.decodeComponent(this._rp.parameters['id']);
        this.id = int.parse(idParam, radix:10);

        this.crumbs = [
            new Breadcrumb('QuickPin', '/'),
            new Breadcrumb('Profiles', '/profile'),
            new Breadcrumb(this.id.toString()),
        ];

        // Add event listeners...
        List<StreamSubscription> listeners = [
            this._sse.onAvatar.listen(this._avatarListener),
            this._sse.onProfile.listen((_) => this._fetchProfile()),
            this._sse.onProfilePosts.listen((_) => this._fetchPosts()),
            this._sse.onProfileRelations.listen((_) {
                this._fetchFriends().then((_) => this._fetchFollowers());
            }),
        ];

        // ...and remove event listeners when we leave this route.
        RouteHandle rh = this._rp.route.newHandle();
        rh.onLeave.take(1).listen((e) {
            listeners.forEach((listener) => listener.cancel());
        });

        // Fetch data for this view.
        this._fetchProfile()
            .then((_) => this._fetchPosts())
            .then((_) => this._fetchFriends())
            .then((_) => this._fetchFollowers());
    }

    /// Listen for avatar image updates.
    void _avatarListener(Event e) {
        Map json = JSON.decode(e.data);
        this.profile.avatarUrl = json['url'];
    }

    /// Fetch a page of followers for this profile.
    Future _fetchFollowers() {
        Completer completer = new Completer();
        this.loading++;
        String url = '/api/profile/${this.id}/relations/followers';
        Map urlArgs = {'page': 1, 'rpp': 10};

        this.api
            .get(url, urlArgs: urlArgs, needsAuth: true)
            .then((response) {
                List followers = response.data['relations'];
                this.followers = new List<Profile>.generate(followers.length, (index) {
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
        String url = '/api/profile/${this.id}/relations/friends';
        Map urlArgs = {'page': 1, 'rpp': 10};

        this.api
            .get(url, urlArgs: urlArgs, needsAuth: true)
            .then((response) {
                List friends = response.data['relations'];
                this.friends = new List<Profile>.generate(friends.length, (index) {
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

        this.api
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

        this.api
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
