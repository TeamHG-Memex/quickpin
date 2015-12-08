import 'dart:async';
import 'dart:convert';
import 'dart:html';

import 'package:angular/angular.dart';
import 'package:bootjack/bootjack.dart';
import 'package:collection/equality.dart';
import 'package:dialog/dialogs/alert.dart';

import 'package:dquery/dquery.dart';
import 'package:quickpin/authentication.dart';
import 'package:quickpin/component/breadcrumbs.dart';
import 'package:quickpin/component/pager.dart';
import 'package:quickpin/model/label.dart';
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
    bool newQP = false;
    List<Profile> profiles;
    Map<String, Map<String, Profile>> newProfilesMap;
    Map<num, Profile> idProfilesMap;
    Pager pager;
    List<String> profileAlerts;
    List<Label> labels;
    Scope scope;
    bool showAdd = false;
    String siteFilter, siteFilterDescription;
    String stubFilter, stubFilterDescription;
    String interestFilter, interestFilterDescription;
    String sortByDescription = 'Added';
    String sortByCol = 'added';
    String sortOrder = 'desc';
    bool submittingProfile = false;
    bool updatingProfile = false;
    List<String> labelFilters;
    String labelFilterDescription;

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
        this.initCurrentPage(this._rp.route, this._fetchCurrentPage);
        this._ts.title = 'Profiles';
        this._parseQueryParameters(this._rp.route.queryParameters);
        this.idProfilesMap = new Map<num, Profile>();
        this.newProfilesMap = new Map<String, Map<String, Profile>>();

        // Add event listeners...
        RouteHandle rh = this._rp.route.newHandle();

        List<StreamSubscription> listeners = [
            this._sse.onAvatar.listen(this.avatarListener),
            this._sse.onProfile.listen(this.profileListener),
            this._sse.onLabel.listen(this.labelListener),
            rh.onEnter.listen((e) {
                this._parseQueryParameters(e.queryParameters);
                if (this.newQP) {
                    new Timer(new Duration(seconds:1), () {
                        this._fetchCurrentPage();
                        this._fetchLabels();
                        this.newQP = false;
                    }); 
                }
            }),
        ];

        // ...and remove event listeners when we leave this route.
        rh.onLeave.take(1).listen((e) {
            listeners.forEach((listener) => listener.cancel());
        });

        this._fetchCurrentPage();
        this._fetchLabels();
    }

    /// Listen for avatar image updates.
    void avatarListener(Event e) {
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
        this.newQP = true;
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
        this.newQP = true;
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
                    args['label'] += ',${label}';
                }
            } else {
                args['label'] = label;
            }
        }
        this.newQP = true;
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
            this.newQP = true;
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
        this.newQP = true;
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
        this.newQP = true;
        this._router.go('profile_list',
                        this._rp.route.parameters,
                        queryParameters: args);
    }

    /// Sort profile list by specified attribute.
    void sortToggle() {
        Map args = this._makeUrlArgs();
        
        if (this.sortByCol != null) {
            if (this.sortByCol.startsWith('-')) {
                this.sortByCol = this.sortByCol.replaceFirst('-', '');
            } else {
                this.sortByCol = '-${this.sortByCol}'; 
            }
            args['sort'] = this.sortByCol;
            this.newQP = true;
            this._router.go('profile_list',
                            this._rp.route.parameters,
                            queryParameters: args);
        }
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
    void profileListener(Event e) {
        Map json = JSON.decode(e.data);
        Profile profile;
        bool showError;
        Map siteProfiles = this.newProfilesMap[json['site']];
        bool thisClient = false;
        String username = json['username'].toLowerCase();

        // May be an update to existing profile.
        // As you cannot edit profiles in list view, this is event is from another client
        this.profiles.forEach((existingProfile) {
            if(existingProfile.id == json['id']) {
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

        // Only process if there is not an error on the profile event
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
            profile.username = json['username'];
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
        else if(thisClient) {
            // Only show errors on events triggered by this client
            profile.error = json['error'];
        }

        if (this.scope != null) {
            scope.apply();
            this.scope.broadcast('masonry.layout');
        }
    }

    /// Listen for label updates.
    void labelListener(Event e) {
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
            'page': this.currentPage,
            'rpp': this._resultsPerPage,
        };

        if (this.siteFilter != null) {
            urlArgs['site'] = this.siteFilter;
        }

        if (this.interestFilter != null) {
            urlArgs['interesting'] = this.interestFilter;
        }

        if (this.labelFilters != null) {
            urlArgs['label'] = this.labelFilters.join(',');
        }

        if (this.stubFilter != null) {
            urlArgs['stub'] = this.stubFilter;
        }

        if (this.sortByCol != null) {
            urlArgs['sort'] = this.sortByCol;
        }

        this.api
            .get(pageUrl, urlArgs: urlArgs, needsAuth: true)
            .then((response) {
                this.profiles = new List.generate(
                    response.data['profiles'].length,
                    (index) => new Profile.fromJson(response.data['profiles'][index])
                );

                this.pager = new Pager(response.data['total_count'],
                                       this.currentPage,
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

    /// Take a map of query parameters and parse/load into member variables.
    void _parseQueryParameters(qp) {
        this.error = null;
        String site = this._getQPString(qp['site']);
        this.siteFilter = site;
        String interesting = this._getQPString(qp['interesting']);
        this.interestFilter = interesting;
        String stub = this._getQPString(qp['stub']);
        this.stubFilter = stub;
        this. sortByCol = this._getQPString(qp['sort']);
        String labels = this._getQPString(qp['label']);

        if (site == null) {
            this.siteFilterDescription = 'All Sites';
        } else {
            String initial = site[0].toUpperCase();
            this.siteFilterDescription = site.replaceRange(0, 1, initial);
        }

        if (interesting == null) {
            this.interestFilterDescription = 'All Profiles';
        } else {
            String initial = interesting[0].toUpperCase();
            this.interestFilterDescription = interesting.replaceRange(0, 1, initial);
        }

        if (labels == null) {
            this.labelFilterDescription = 'All Labels';
            this.labelFilters = null; 
        } else {
            this.labelFilters = labels.split(','); 
            this.labelFilters.sort();
            this.labelFilterDescription = '${this.labelFilters.length.toString()} active';
        }
        if (stub == null) {
            this.stubFilterDescription = 'All Profiles';
        } else if (stub == '1'){
            this.stubFilterDescription = 'Yes';
        } else {
            this.stubFilterDescription = 'No';
        }

        if (this.sortByCol == null) {
            this.sortByDescription = 'Added';
        } else {
            this.sortByDescription = this.sortByCol.replaceFirst('-', '');
            String initial = sortByDescription[0].toUpperCase();
            this.sortByDescription = this.sortByDescription.replaceRange(0, 1, initial);
            if(!this.sortByCol.startsWith('-')) {
                this.sortOrder = 'asc';
            } else {
                this.sortOrder = 'desc';
            }
        }
    }
}
