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
    Map<String, Map<String, Profile>> newProfilesMap;
    Map<num, Profile> idProfilesMap;
    Scope scope;
    bool showAdd = false;
    bool submittingProfile = false;

    InputElement _inputEl;

    final RestApiController api;
    final AuthenticationController auth;
    final Element _element;
    final int _resultsPerPage = 10;
    final RouteProvider _rp;
    final SseController _sse;
    final TitleService _ts;

    /// Constructor.
    ProfileListComponent(this.api, this.auth, this._element, this._rp,
                         this._sse, this._ts) {
        this._fetchCurrentPage();
        this._ts.title = 'Profiles';
        this.idProfilesMap = new Map<num, Profile>();
        this.newProfilesMap = new Map<String, Map<String, Profile>>();

        // Add event listeners...
        List<StreamSubscription> listeners = [
            this._sse.onAvatar.listen(this.avatarListener),
            this._sse.onProfile.listen(this.profileListener),
        ];

        // ...and remove event listeners when we leave this route.
        RouteHandle rh = this._rp.route.newHandle();
        rh.onLeave.take(1).listen((e) {
            listeners.forEach((listener) => listener.cancel());
        });
    }

    /// Listen for avatar image updates.
    void avatarListener(Event e) {
        Map json = JSON.decode(e.data);

        this.idProfilesMap[json['id']].avatarUrl = json['url'];

        if (this.scope != null) {
            scope.apply();
            this.scope.broadcast('masonry.layout');
        }
    }

    /// Submit a new profile.
    void addProfile() {
        Profile profile = this._newProfile(this.newProfile);
        String pageUrl = '/api/profile/';
        Map body = {'profiles': [{'username': this.newProfile, 'site': 'twitter'}]};
        this.error = null;
        this.submittingProfile = true;

        this.api
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

    /// Remove a profile at the specified index. (Usually done because of an
    /// error creating or fetching the profile.)
    void dismissProfileAtIndex(int index) {
        this.profiles.removeAt(index);
        this.scope.broadcast('masonry.layout');
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
    ///
    /// TODO: This will need to be modified to respect the client's current
    /// filter, when the filtering feature is implemented.
    void profileListener(Event e) {
        bool showError;
        Map json = JSON.decode(e.data);
        String username = json['username'].toLowerCase();
        Map siteProfiles = this.newProfilesMap[json['site']];
        Profile profile;

        if (siteProfiles != null) {
            profile = siteProfiles[username];
        }

        if (json['error'] == null) {
            if (profile == null) {
                // This must be a profile started in a different client.
                profile = this._newProfile(username);
            }

            profile.id = json['id'];
            profile.description = json['description'];
            profile.friendCount = json['friend_count'];
            profile.followerCount = json['follower_count'];
            profile.postCount = json['post_count'];
            profile.username = json['username'];

            this.idProfilesMap[json['id']] = profile;
            this.newProfilesMap[json['site']].remove(username);
        } else if (profile != null) {
            // Only display errors for profiles added by this client.
            profile.error = json['error'];
        }

        if (this.scope != null) {
            scope.apply();
            this.scope.broadcast('masonry.layout');
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

    /// Fetch a page of profiles.
    void _fetchCurrentPage() {
        this.error = null;
        this.loading = true;
        String pageUrl = '/api/profile/';

        this.api
            .get(pageUrl, needsAuth: true)
            .then((response) {
                this.profiles = new List.generate(
                    response.data['profiles'].length,
                    (index) => new Profile.fromJson(response.data['profiles'][index])
                );

                if (this.scope != null) {
                    this.scope.broadcast('masonry.layout');
                }
            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {this.loading = false;});
    }

    /// Create an empty profile object and insert it into the profile list.
    Profile _newProfile(String username) {
        Profile profile = new Profile(username, 'twitter');
        profile.avatarUrl = '/static/img/default_user.png';
        this.profiles.insert(0, profile);

        if (this.newProfilesMap['twitter'] == null) {
            this.newProfilesMap['twitter'] = new Map<String, Profile>();
        }

        this.newProfilesMap['twitter'][username.toLowerCase()] = profile;

        // Update layout after Angular finishes next digest cycle.
        new Timer(new Duration(milliseconds: 100), () {
            if (this.scope != null) {
                this.scope.broadcast('masonry.layout');
            }
        });

        return profile;
    }
}
