import 'dart:async';
import 'dart:convert';
import 'dart:html';

import 'package:angular/angular.dart';
import 'package:bootjack/bootjack.dart';
import 'package:collection/equality.dart';
import 'package:dialog/dialogs/alert.dart';

import 'package:dquery/dquery.dart';
import 'package:quickpin/authentication.dart';
import 'package:quickpin/query_watcher.dart';
import 'package:quickpin/component/breadcrumbs.dart';
import 'package:quickpin/component/pager.dart';
import 'package:quickpin/model/label.dart';
import 'package:quickpin/component/title.dart';
import 'package:quickpin/model/profile.dart';
import 'package:quickpin/rest_api.dart';
import 'package:quickpin/sse.dart';

/// A component for listing profiles.
@Component(
    selector: 'profile-list',
    templateUrl: 'packages/quickpin/component/profile/list.html',
    useShadowDom: false
)
class ProfileListComponent extends Object
                           implements ScopeAware, ShadowRootAware {
    List<Breadcrumb> crumbs = [
        new Breadcrumb('QuickPin', '/'),
        new Breadcrumb('Profiles'),
    ];

    String error;
    InputElement _inputEl;
    String interestFilter, interestFilterDescription;
    Map<String> filterDescriptions;
    List<Label> labels;
    List<String> labelFilters;
    String labelFilterDescription;
    bool loading = false;
    String newProfile, newProfileSite;
    String newProfileSiteDescription = 'Select A Site';
    Pager pager;
    List<Profile> profiles;
    Map<String, Map<String, Profile>> newProfilesMap;
    Map<num, Profile> idProfilesMap;
    List<String> profileAlerts;
    QueryWatcher _queryWatcher;

    Scope scope;
    bool showAdd = false;
    String siteFilter, siteFilterDescription;
    String stubFilter, stubFilterDescription;
    String sortByDescription = 'Added';
    String sortByCol = 'added';
    String sortOrder = 'desc';
    bool submittingProfile = false;
    bool updatingProfile = false;


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
        this.idProfilesMap = new Map<num, Profile>();
        this.newProfilesMap = new Map<String, Map<String, Profile>>();

        // Add event listeners...
        RouteHandle rh = this._rp.route.newHandle();

        UnsubOnRouteLeave(rh, [
            this._sse.onAvatar.listen(this._avatarListener),
            this._sse.onProfile.listen(this._profileListener),
            this._sse.onLabel.listen(this._labelListener)
        ]);

        this._queryWatcher = new QueryWatcher(
            rh,
            ['page', 'sort', 'site', 'interesting', 'label', 'stub'],
            this._fetchCurrentPage
        );

        this._fetchCurrentPage();
        this._fetchLabels();
    }

    /// Convert a string to title case.
    String toTitleCase(String s) {
        if (s == null) {
            return null;
        }
        List words = s.split(' ');
        String titleCaseString = '';
        words.forEach((word) {
           String titleCaseWord = '${word[0].toUpperCase()}${word.substring(1)}';
           titleCaseString = '${titleCaseString} ${titleCaseWord}';
        });
        return titleCaseString.trim();
    }

    // Set human-friendly filter descriptions.
    void _setFilterDescriptions() {
        this.filterDescriptions = {
            'site': this.toTitleCase(this._queryWatcher['site']) ?? 'All Sites',
            'interesting': this.toTitleCase(this._queryWatcher['interesting']) ?? 'All profiles'
        };

        if (this._queryWatcher['stub'] == '1') {
            this.filterDescriptions['stub'] = 'Yes';
        } else if(this._queryWatcher['stub'] == '0') {
            this.filterDescriptions['stub'] = 'No';
        } else {
            this.filterDescriptions['stub'] = 'All Profiles';
        }

        if (this._queryWatcher['label'] != null)  {
            this.labelFilters = this._queryWatcher['label'].split(',');
            this.filterDescriptions['label'] = '${this.labelFilters.length} active';
        } else {
            this.filterDescriptions['label'] = 'All Labels';
            this.labelFilters = null;
        }

        if (this._queryWatcher['sort'] != null) {
            this.filterDescriptions['sort'] = this.toTitleCase(this._queryWatcher['sort'].replaceFirst('-', ''));
            if (this._queryWatcher['sort'][0] == '-') {
                this.sortOrder = 'desc';
            } else {
                this.sortOrder = 'asc';
            }
        } else {
            this.filterDescriptions['sort'] = 'Added';
            this.sortOrder = 'desc';
        }

    }

    /// Listen for avatar image updates.
    void _avatarListener(Event e) {
        Map json = JSON.decode(e.data);
        Profile profile = this.idProfilesMap[json['id']];

        if (profile != null) {
            profile.avatarUrl = json['url'];
        }

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

    /// Fetch list of labels.
    Future _fetchLabels() {
        Completer completer = new Completer();
        this.loading = true;
        String pageUrl = '/api/label/';
        int page = 1;
        bool finished = false;
        this.labels = new List<Label>();
        int totalCount = 0;

        while (!finished) {
            Map urlArgs = {
                'rpp': 100,
                'page': page
            };
            new Future(() {
                this.api
                    .get(pageUrl, urlArgs: urlArgs, needsAuth: true)
                    .then((response) {
                        response.data['labels'].forEach((label) {
                            this.labels.add(new Label.fromJson(label));

                        });
                        if (response.data.containsKey('total_count')) {
                            totalCount = response.data['total_count'];
                        } else {
                            finished = true;
                        }

                    })
                    .catchError((response) {
                        this.labelError = response.data['message'];
                    })
                    .whenComplete(() {
                    });
            });

            if (totalCount == this.labels.length) {
                finished = true;
            }
            else {
                page++;
            }
        };
        this.loading = false;
        completer.complete();
        return completer.future;
    }

    /// Remove a profile at the specified index. (Usually done because of an
    /// error creating or fetching the profile.)
    void dismissProfileAtIndex(int index) {
        this.profiles.removeAt(index);
        this.scope.broadcast('masonry.layout');
    }

    /// Set interest status of profile at index.
    void setProfileInterestAtIndex(int index, [bool isInteresting]) {
        Profile profile = this.profiles[index];
        int profileID = profile.id;
        Map args = this._makeUrlArgs();
        String pageUrl = '/api/profile/${profileID.toString()}';
        this.error = null;
        this.loading = true;

        Map body = {
            'is_interesting': isInteresting,
        };

        // Map
        Map interestFilterMap = {
            'yes': true,
            'no': false,
            'unset': null,
        };

        this.api
            .put(pageUrl, body, needsAuth: true)
            .then((response) {
                //new Timer(new Duration(seconds:0.1), () => this._inputEl.focus());
                profile.isInteresting = isInteresting;

                if(this.interestFilter != null) {
                    if(isInteresting != interestFilterMap[this.interestFilter]){
                        this.profiles.removeAt(index);
                    }
                }
                this.scope.broadcast('masonry.layout');
            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {
                this.loading = false;
            });
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

    /// Filter profile list by a specified interest level.
    void filterInterest(String interesting) {
        Map args = this._makeUrlArgs();

        if (interesting == null) {
            args.remove('interesting');
        } else {
            args['interesting'] = interesting;
        }
        this._router.go('profile_list',
                        this._rp.route.parameters,
                        queryParameters: args);
    }

    /// Filter profile list by labels.
    void filterLabels(String label) {
        Map args = this._makeUrlArgs();

        if (label == null) {
            args.remove('label');
        } else {
            if (this.labelFilters != null) {
                if (!this.labelFilters.contains(label)) {
                    this.labelFilters.add(label);
                }
            } else {
                this.labelFilters = [label];
            }

            if (this.labelFilters.length == 0) {
                args.remove('label');
                this.labelFilters = null;
            } else {
                args['label'] = this.labelFilters.join(',');
            }
        }
        this._router.go('profile_list',
                        this._rp.route.parameters,
                        queryParameters: args);
    }

    /// Remove specified label from list of profile label filters.
    void filterLabelsRemove(String label) {
        Map args = this._makeUrlArgs();
        if (this.labelFilters != null) {
            List labels = new List();
            this.labelFilters.forEach((labelFilter) {
                if (labelFilter != label) {
                    labels.add(labelFilter);
                }
            });
            if (labels.length == 0) {
                args.remove('label');
            } else {
                args['label'] = labels.join(',');
            }
            this._router.go('profile_list',
                            this._rp.route.parameters,
                            queryParameters: args);
        }
    }

    /// Filter profile list by specified stub value.
    void filterStub(String stub) {
        Map args = this._makeUrlArgs();

        if (stub == null) {
            args.remove('stub');
        } else {
            args['stub'] = stub;
        }
        this._router.go('profile_list',
                        this._rp.route.parameters,
                        queryParameters: args);
    }

    /// Sort profile list by specified attribute.
    void sortBy(String attr, bool asc) {
        Map args = this._makeUrlArgs();

        if (attr == null) {
            args.remove('sort');
        } else {
            args['sort'] = attr;
        }
        this._router.go('profile_list',
                        this._rp.route.parameters,
                        queryParameters: args);
    }

    /// Set order of sort column.
    void sortToggle() {
        Map args = this._makeUrlArgs();

        if (this._queryWatcher['sort'] != null) {
            if (this._queryWatcher['sort'].startsWith('-')) {
                args['sort'] = this._queryWatcher['sort'].replaceFirst('-', '');
            } else {
                args['sort'] = '-${this._queryWatcher["sort"]}';
            }
        } else {
            args['sort'] = '-added';
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

    // Return whether profile json should be filtered from the current view.
    bool _isFiltered(profile_json) {
        bool filtered = true;
        bool interestFiltered = true;
        bool labelFiltered = true;
        List<String> labels = new List<String>();
        bool siteFiltered = true;
        bool stubFiltered = true;

        // Determine if the profile is filtered by 'site'.
        if (profile_json['site'] == this.siteFilter || this.siteFilter == null) {
            siteFiltered = false;
        }
        // Determine if profile is filtered by 'is_interesting'.
        if (profile_json['is_interesting'] == this.interestFilter || this.interestFilter == null) {
            interestFiltered = false;
        }
        // Determine if the profile is filtered by 'is_stub'.
        if ((profile_json['is_stub'] && this.stubFilter == '1')
                || (!profile_json['is_stub'] && this.stubFilter == '0')
                || this.stubFilter == null) {
            stubFiltered = false;
        }
        // Determine if the profile is filtered by label.
        profile_json['labels'].forEach((label_json) {
            labels.add(label_json['text']);
        });
        labels.sort();
        Function eq = const ListEquality().equals;
        if (eq(labels, this.labelFilters) || this.labelFilters == null) {
            labelFiltered = false;
        }
        // If any filters apply, the profile is filtered.
        if (!siteFiltered && !interestFiltered && !stubFiltered && !labelFiltered) {
            filtered = false;
        }
        return filtered;
    }

    /// Listen for profile updates.
    void _profileListener(Event e) {
        Map json = JSON.decode(e.data);
        Profile profile;
        bool showError;
        Map siteProfiles = this.newProfilesMap[json['site']];
        bool thisClient = false;
        String username;
        window.console.debug(e);

        // When a profile is returned, the json has
        // a 'username'.
        // When there is an error, the json contains
        // 'usernames',
        // This is a result of the Twitter API returning 200
        // status codes when the 'accept' a batch request, rather than
        // if the username doesn't exist.
        if (json['error'] == null) {
          username = json['username'].toLowerCase();
        } else {
          // Currently the client can only submit 1 username at a time
          // so the username will always be the first index.
          // If/when batch usernames can be submitted this
          // will need to be updated accordingly
          username = json['usernames'][0].toLowerCase();
        }

        // May be an update to existing profile.
        // As you cannot edit profiles in list view, this event is from another client
        this.profiles.forEach((existingProfile) {
            if(json['id'] != null && existingProfile.id == json['id']) {
                profile = existingProfile;
            }
        });

        // May be a new profile added by this client
        if (profile == null && siteProfiles != null) {
            if (siteProfiles.containsKey(username)) {
                profile = siteProfiles[username];
                thisClient = true;
            }
        }

        // Only process the profile if there is not an error
        if (json['error'] == null) {
            // If profile still null it is a profile added by another client
            if (profile == null) {
                profile = this._newProfile(username, json['site']);
            }
            profile.id = json['id'];
            profile.description = json['description'];
            profile.friendCount = json['friend_count'];
            profile.followerCount = json['follower_count'];
            profile.postCount = json['post_count'];
            profile.username = username;
            profile.isInteresting = json['is_interesting'];
            profile.score = json['score'];
            if (this.newProfilesMap[json['site']] != null) {
                this.newProfilesMap[json['site']].remove(username);
            }
            if (!this._isFiltered(json)){
                this.idProfilesMap[json['id']] = profile;
            }
            else if (thisClient) {
                String message = """
                    You added a profile that is filtered from your current view.
                    Reset your filters to view all profiles.
                    """;
                this.profileAlerts.add(message);
                new Timer(new Duration(seconds:2), () {
                    //alert('Yo!');
                    this.idProfilesMap[json['id']] = profile;
                    this.idProfilesMap.remove(json['id']);
                    this.profiles.remove(profile);
                    if (this.scope != null) {
                        scope.apply();
                        this.scope.broadcast('masonry.layout');
                    }
                });
            }

        }
        else if (thisClient) {
            // Only show errors on events triggered by this client
            profile.error = json['error'];
        }

        if (this.scope != null) {
            scope.apply();
            this.scope.broadcast('masonry.layout');
        }
    }

    /// Listen for label updates.
    void _labelListener(Event e) {
        Map json = JSON.decode(e.data);

        if (json['error'] == null) {
            this._fetchLabels();
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
        this.profileAlerts = new List<String>();
        this.loading = true;
        String pageUrl = '/api/profile/';
        Map urlArgs = {
            'page': this._queryWatcher['page'] ?? '1',
            'rpp': this._resultsPerPage,
        };

        if (this._queryWatcher['site'] != null) {
            urlArgs['site'] = this._queryWatcher['site'];
        }

        if (this._queryWatcher['interesting'] != null) {
            urlArgs['interesting'] = this._queryWatcher['interesting'];
        }

        if (this._queryWatcher['label'] != null) {
            urlArgs['label'] = this._queryWatcher['label'];
        }

        if (this._queryWatcher['stub'] != null) {
            urlArgs['stub'] = this._queryWatcher['stub'];
        }

        if (this._queryWatcher['sort'] != null) {
            urlArgs['sort'] = this._queryWatcher['sort'];
        }

        this.api
            .get(pageUrl, urlArgs: urlArgs, needsAuth: true)
            .then((response) {
                this.profiles = new List.generate(
                    response.data['profiles'].length,
                    (index) => new Profile.fromJson(response.data['profiles'][index])
                );

                this.pager = new Pager(response.data['total_count'],
                                       int.parse(this._queryWatcher['page'] ?? '1'),
                                       resultsPerPage:this._resultsPerPage);

                new Timer(new Duration(milliseconds: 100), () {
                    if (this.scope != null) {
                        this.scope.broadcast('masonry.layout');
                    }
                });
            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {
                this._setFilterDescriptions();
                this.loading = false;
            });
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

        if (this.interestFilter != null) {
            args['interesting'] = this.interestFilter;
        }

        if (this.labelFilters != null) {
            args['label'] = this.labelFilters.join(',');
        }

        if (this.stubFilter != null) {
            args['stub'] = this.stubFilter;
        }

        if (this.sortByCol != null) {
            args['sort'] = this.sortByCol;
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

}
