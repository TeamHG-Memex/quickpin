import 'dart:async';
import 'dart:html';
import 'dart:js';

import 'package:angular/angular.dart';
import 'package:quickpin/authentication.dart';
import 'package:quickpin/component/breadcrumbs.dart';
import 'package:quickpin/component/title.dart';
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
    int id;
    int loading = 0;
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

        this._fetchProfile();
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

    /// Fetch data about this profile.
    Future _fetchProfile() {
        Completer completer = new Completer();
        this.loading++;

        this._api
            .get('/api/profile/${this.id}', needsAuth: true)
            .then((response) {
                this.profile = new Profile.fromJson(response.data);
                this.crumbs[this.crumbs.length-1] = new Breadcrumb(this.profile.name);
                this._ts.title = this.profile.name;
            })
            .whenComplete(() {
                this.loading--;
                completer.complete();
            });

        return completer.future;
    }
}
