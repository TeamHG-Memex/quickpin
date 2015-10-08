import 'dart:async';
import 'dart:convert';
import 'dart:html';
import 'dart:js';

import 'package:angular/angular.dart';
import 'package:quickpin/authentication.dart';
import 'package:quickpin/component/breadcrumbs.dart';
import 'package:quickpin/component/title.dart';
import 'package:quickpin/model/label.dart';
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
    bool loadingFailedTasks = false;
    bool showAddLabel = false;
    bool submittingLabel = false;
    bool failedTasks = false;
    List<Label> labels;
    String newLabelText;
    String labelError;
    List<Map> workers;
    List<Map> profileWorkers;
    Map<String, Map> _runningJobs;
    List<Post> posts;
    Profile profile;
    InputElement _inputLabelEl;

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
            this._sse.onWorker.listen(this._workerListener),
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
            .then((_) => this._fetchFollowers())
            .then((_) => this._fetchLabels())
            .then((_) => this._fetchProfileWorkers())
            .then((_) => this._fetchFailedProfileTasks());
    }

    /// Hide the "add label" dialog.
    void hideAddLabelDialog() {
        this.showAddLabel = false;
        this.newLabelText = '';
    }

    /// Show the "add label" dialog.
    void showAddLabelDialog() {
        this.showAddLabel = true;

        if (this._inputLabelEl != null) {
            // Allow Angular to digest showAddLabel before trying to focus. (Can't
            // focus a hidden element.)
            new Timer(new Duration(seconds:0.1), () => this._inputLabelEl.focus());
        }
    }

    /// Get a reference to this element.
    void onShadowRoot(ShadowRoot shadowRoot) {
        this._inputLabelEl = this._element.querySelector('#newLabelText');
    }

    void addProfileLabel() {
        InputElement labelEl = querySelector('#newLabelText');

       
        if (labelEl.value == null || labelEl.value == '') {
            this.labelError = 'You must enter text for the label.';
            return;
        } else {
            this.labelError = null;
        }
        this.profile.labels.add(new Label(labelEl.value));
        this._updateProfileLabels();
        this._updateProfileLabels().then((_) => labelEl.value = '');

    }

    void removeProfileLabelAtIndex(int index) {
        this.profile.labels.removeAt(index);
        this._updateProfileLabels();
    }

    Future _updateProfileLabels() {
        Completer completer = new Completer();

        
        this.submittingLabel = true;
        String pageUrl = '/api/profile/${this.id.toString()}';
        this.loading++;
        List<Map> profileLabels = new List();
        this.profile.labels.forEach((label) {
            profileLabels.add({'name': label.name});
        });

        Map body = {
            'labels': profileLabels, 
        };

        this.api
            .put(pageUrl, body, needsAuth: true)
            .then((response) {
                //profile.labels = profileLabels;
            })
            .catchError((response) {
                this.labelError = response.data['message'];
            })
            .whenComplete(() {
                this.loading--;
                this.submittingLabel = false;
            });

        completer.complete();
        return completer.future;
    }

    /// Listen for avatar image updates.
    void _avatarListener(Event e) {
        Map json = JSON.decode(e.data);
        this.profile.avatarUrl = json['url'];
    }

    /// Listen for updates from background workers.
    void _workerListener(Event e) {
        Map json = JSON.decode(e.data);
        String status = json['status'];

        if (status == 'queued' || status == 'started' || status == 'finished') {
            // This information can only be fetched via REST.
            this._fetchProfileWorkers();
        } else if (status == 'progress') {
            Map job = this._runningJobs[json['id']];

            if (job != null) {
                // Event contains all the data we need: no need for REST call.
                job['current'] = json['current'];
                job['progress'] = json['progress'];
            } else {
                // This is a job we don't know about: needs REST call.
                this._fetchProfileWorkers();
            }
        } else if (status == 'failed') {
            this._fetchFailedProfileTasks().then((_) => this._fetchProfileWorkers());
        }
    }

    /// Set interest status of profile.
    void setProfileInterest([bool isInteresting]) {
        String pageUrl = '/api/profile/${this.id.toString()}';
        this.loading++;

        Map body = {
            'is_interesting': isInteresting, 
        };

        this.api
            .put(pageUrl, body, needsAuth: true)
            .then((response) {
                //new Timer(new Duration(seconds:0.1), () => this._inputEl.focus());
                profile.isInteresting = isInteresting;
            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {
                this.loading--;
            });
    }

    /// Request updated data for profile.
    void updateProfile(Event event, String data, Function resetButton) {
        String pageUrl = '/api/profile/${this.id}/update';
        this.loading++;

        this.api
            .get(pageUrl, needsAuth: true)
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {
                resetButton();
                this.loading--;
            });
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

    /// Fetch worker jobs for profile.
    Future _fetchProfileWorkers() {
        Completer completer = new Completer();

        this.api
            .get('/api/tasks/workers', needsAuth: true)
            .then((response) {
                this.workers = response.data['workers'];
                this.profileWorkers = [];

                this._runningJobs = new Map<String, Map>();

                this.workers.forEach((worker) {
                    Map currentJob = worker['current_job'];

                    if (currentJob != null) {
                        if (currentJob['profile_id'] == this.id) {
                        this._runningJobs[currentJob['id']] = currentJob;
                            this.profileWorkers.add(worker);
                        }
                    }
                });
            })
            .whenComplete(() {
                completer.complete();
            });

        return completer.future;
    }

    /// Fetch failed task data for this profile.
    Future _fetchFailedProfileTasks() {
        Completer completer = new Completer();
        List<Map> failed;
        this.loadingFailedTasks = true;

        this.api
            .get('/api/tasks/failed', needsAuth: true)
            .then((response) {
                failed = response.data['failed'];
                failed.forEach((failed_task) {
                    if (this.id == failed_task['profile_id']) {
                        this.failedTasks = true;
                    }
                });
                
            })
            .whenComplete(() {
                this.loadingFailedTasks = false;
                completer.complete();
            });

        return completer.future;
    }

    /// Fetch list of labels.
    Future _fetchLabels() {
        Completer completer = new Completer();
        this.loading++;
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
        this.loading--;
        completer.complete();
        return completer.future;
    }

}
