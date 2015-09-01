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
    String newProfile, newProfileSite;
    String newProfileSiteDescription = 'Select A Site';
    List<Profile> profiles;
    Map<String, Map<String, Profile>> newProfilesMap;
    Map<num, Profile> idProfilesMap;
    Scope scope;
    bool showAdd = false;
    String siteFilter, siteFilterDescription;
    bool submittingProfile = false;

    InputElement _inputEl;

    final RestApiController api;
    final AuthenticationController auth;
    final Element _element;
    final int _resultsPerPage = 10;
    final Router _router;
    final RouteProvider _rp;
    final SseController _sse;
    final TitleService _ts;

    /// Constructor.
    ProfileListComponent(this.api, this.auth, this._element, this._router,
                         this._rp, this._sse, this._ts) {
        this._ts.title = 'Profiles';
        this._parseQueryParameters(this._rp.route.queryParameters);
        this.idProfilesMap = new Map<num, Profile>();
        this.newProfilesMap = new Map<String, Map<String, Profile>>();

        // Add event listeners...
        RouteHandle rh = this._rp.route.newHandle();

        List<StreamSubscription> listeners = [
            this._sse.onAvatar.listen(this.avatarListener),
            this._sse.onProfile.listen(this.profileListener),
            rh.onEnter.listen((e) {
                this._parseQueryParameters(e.queryParameters);
                this._fetchCurrentPage();
            }),
        ];

        // ...and remove event listeners when we leave this route.
        rh.onLeave.take(1).listen((e) {
            listeners.forEach((listener) => listener.cancel());
        });

        this._fetchCurrentPage();
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
        if (this.newProfileSite == null) {
            this.error = 'You must select a social media site before you can'
                         ' add a profile.';
            return;
        } else {
            this.error = null;
        }

        Profile profile = this._newProfile(this.newProfile,
                                           this.newProfileSite);
        String pageUrl = '/api/profile/';
        this.error = null;
        this.submittingProfile = true;

        Map body = {
            'profiles': [{
                'username': this.newProfile,
                'site': this.newProfileSite,
            }],
        };

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

    /// Filter profile list by a specified site.
    void filterSite(String site) {
        Map args = this._makeUrlArgs();

        if (site == null) {
            args.remove('site');
        } else {
            args['site'] = site;
        }

        this._router.go('profile_list',
                        this._rp.route.parameters,
                        queryParameters: args);
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
        bool showError;
        Map json = JSON.decode(e.data);
        String username = json['username'].toLowerCase();
        Map siteProfiles = this.newProfilesMap[json['site']];
        Profile profile;

        if (siteProfiles != null) {
            profile = siteProfiles[username];
        }

        if (json['error'] == null) {
            if (profile == null &&
                (this.siteFilter == null || this.siteFilter == json['site'])) {
                // This was added by another client.
                profile = this._newProfile(username, json['site']);
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

    /// Select a site in the "Add Profile" form.
    void selectAddProfileSite(String site) {
        this.newProfileSite = site;
        String siteHuman = site.replaceRange(0, 1, site[0].toUpperCase());
        this.newProfileSiteDescription = 'On ' + siteHuman;
    }

    /// Fetch a page of profiles.
    void _fetchCurrentPage() {
        this.error = null;
        this.loading = true;
        String pageUrl = '/api/profile/';
        Map urlArgs = new Map();

        if (this.siteFilter != null) {
            urlArgs['site'] = this.siteFilter;
        }

        this.api
            .get(pageUrl, urlArgs: urlArgs, needsAuth: true)
            .then((response) {
                this.profiles = new List.generate(
                    response.data['profiles'].length,
                    (index) => new Profile.fromJson(response.data['profiles'][index])
                );

                new Timer(new Duration(milliseconds: 100), () {
                    if (this.scope != null) {
                        this.scope.broadcast('masonry.layout');
                    }
                });
            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {this.loading = false;});
    }

    /// Get a query parameter as an int.
    void _getQPInt(value, [defaultValue]) {
        if (value != null) {
            return int.parse(value);
        } else {
            return defaultValue;
        }
    }

    /// Get a query parameter as a string.
    void _getQPString(value, [defaultValue]) {
        if (value != null) {
            return Uri.decodeComponent(value);
        } else {
            return defaultValue;
        }
    }

    /// Make a map of arguments for a URL query string.
    void _makeUrlArgs() {
        var args = new Map<String>();

        if (this.siteFilter != null) {
            args['site'] = this.siteFilter;
        }

        return args;
    }

    /// Create an empty profile object and insert it into the profile list.
    Profile _newProfile(String username, String site) {
        Profile profile = new Profile(username, site);
        profile.avatarUrl = '/static/img/default_user.png';
        profile.siteName = site.replaceRange(0, 1, site[0].toUpperCase());
        this.profiles.insert(0, profile);

        if (this.newProfilesMap[site] == null) {
            this.newProfilesMap[site] = new Map<String, Profile>();
        }

        this.newProfilesMap[site][username.toLowerCase()] = profile;

        // Update layout after Angular finishes next digest cycle.
        new Timer(new Duration(milliseconds: 100), () {
            if (this.scope != null) {
                this.scope.broadcast('masonry.layout');
            }
        });

        return profile;
    }

    /// Take a map of query parameters and parse/load into member variables.
    void _parseQueryParameters(qp) {
        this.error = '';
        String site = this._getQPString(qp['site']);
        this.siteFilter = site;

        if (site == null) {
            this.siteFilterDescription = 'All Sites';
        } else {
            String initial = site[0].toUpperCase();
            this.siteFilterDescription = site.replaceRange(0, 1, initial);
        }
    }
}
