import 'dart:async';
import 'dart:convert';
import 'dart:html';

import 'package:angular/angular.dart';
import 'package:quickpin/authentication.dart';
import 'package:quickpin/component/breadcrumbs.dart';
import 'package:quickpin/component/title.dart';
import 'package:quickpin/mixin/current_page.dart';
import 'package:quickpin/model/profile.dart';
import 'package:quickpin/rest_api.dart';
import 'package:quickpin/sse.dart';

/// A component for listing profiles.
@Component(
    selector: 'profile-list',
    templateUrl: 'packages/quickpin/component/profile/list.html',
    useShadowDom: false
)
class ProfileListComponent extends Object with CurrentPageMixin
                           implements ScopeAware, ShadowRootAware {
    List<Breadcrumb> crumbs = [
        new Breadcrumb('QuickPin', '/'),
        new Breadcrumb('Profiles'),
    ];

    String error;
    bool loading = false;
    String newProfile;
    List<Profile> profiles;
    Map<List, Profile> newProfilesMap;
    Map<num, Profile> idProfilesMap;
    Scope scope;
    bool showAdd = false;
    bool submittingProfile = false;

    InputElement _inputEl;

    final AuthenticationController auth;
    final RestApiController _api;
    final Element _element;
    final int _resultsPerPage = 10;
    final RouteProvider _rp;
    final SseController _sse;
    final TitleService _ts;

    /// Constructor.
    ProfileListComponent(this.auth, this._api, this._element, this._rp,
                         this._sse, this._ts) {
        this._fetchCurrentPage();
        this._ts.title = 'Profiles';
        this.idProfilesMap = new Map<num, Profile>();
        this.newProfilesMap = new Map<List, Profile>();

        // Add event listeners...
        StreamSubscription avatarSub = this._sse.onAvatar.listen(this.avatarListener);
        StreamSubscription profileSub = this._sse.onProfile.listen(this.profileListener);

        // ...and remove event listeners when we leave this route.
        RouteHandle rh = this._rp.route.newHandle();
        rh.onLeave.take(1).listen((e) {
            avatarSub.cancel();
            profileSub.cancel();
        });
    }

    /// Listen for avatar image updates.
    void avatarListener(Event e) {
        Map json = JSON.decode(e.data);

        this.idProfilesMap[json['id']].avatarUrls.add(json['url']);

        if (this.scope != null) {
            scope.apply();
        }
    }

    /// Submit a new profile.
    void addProfile() {
        this.error = null;
        this.submittingProfile = true;
        String pageUrl = '/api/profile/';
        Map body = {'profiles': [{'name': this.newProfile, 'site': 'twitter'}]};
        Profile profile = new Profile(this.newProfile, 'twitter');
        this.profiles.insert(0, profile);
        String key = _makeKey(this.newProfile, 'twitter');
        this.newProfilesMap[key] = profile;

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

    /// Remove a profile at the specified index. (Usually done because of an
    /// error creating or fetching the profile.)
    void dismissProfileAtIndex(int index) {
        this.profiles.removeAt(index);
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

    /// Listen for profile updates.
    void profileListener(Event e) {
        Map json = JSON.decode(e.data);
        List key = _makeKey(json['name'], json['site']);
        Profile profile = this.newProfilesMap[key];

        if (json['error'] == null) {
            profile.id = json['id'];
            profile.description = json['description'];
            profile.friendCount = json['friend_count'];
            profile.followerCount = json['follower_count'];
            profile.postCount = json['post_count'];

            this.idProfilesMap[json['id']] = profile;
        } else {
            profile.error = json['error'];
        }

        if (this.scope != null) {
            scope.apply();
        }
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

    /// Called via ScopeAware interface.
    void setScope(Scope scope) {
        this.scope = scope;
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

    /// Make a map key from a username and site name.
    String _makeKey(String user, String site) {
        return '{{user}\0{{site}}';
    }
}
