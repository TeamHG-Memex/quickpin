import 'dart:async';
import 'dart:convert';

import 'package:angular/angular.dart';
import 'package:quickpin/authentication.dart';
import 'package:quickpin/component/breadcrumbs.dart';
import 'package:quickpin/component/pager.dart';
import 'package:quickpin/component/title.dart';
import 'package:quickpin/mixin/current_page.dart';
import 'package:quickpin/model/profile.dart';
import 'package:quickpin/rest_api.dart';
import 'package:quickpin/sse.dart';

/// A component for posts by a specified profile.
@Component(
    selector: 'profile-relations',
    templateUrl: 'packages/quickpin/component/profile/relations.html',
    useShadowDom: false
)
class ProfileRelationsComponent extends Object with CurrentPageMixin
                                implements ScopeAware {

    AuthenticationController auth;
    List<Breadcrumb> crumbs;
    String error = '';
    bool failedTasks = false;
    String id;
    int loading = 0;
    Pager pager;
    List<Profile> relations;
    Scope scope;
    String siteName;
    String username;
    Map<String, Map> _runningJobs;
    List<Map> workers;
    List<Map> profileRelationsWorkers;

    String _relType;

    final RestApiController api;
    final RouteProvider _rp;
    final int _resultsPerPage = 30;
    final TitleService _ts;
    final SseController _sse;

    /// Constructor.
    ProfileRelationsComponent(this.api, this.auth, this._rp, this._sse, this._ts) {
        this.initCurrentPage(this._rp.route, this._fetchCurrentPage);
        this.id = this._rp.parameters['id'];
        this._relType = this._rp.parameters['reltype'];
        this._ts.title = 'Posts by ${id}';
        this._updateCrumbs();
        this._fetchCurrentPage()
            .then((_) => this._fetchProfileRelationsWorkers())
            .then((_) => this._fetchFailedProfileRelationsTasks());


        // Add event listeners...
        List<StreamSubscription> listeners = [
            this._sse.onProfileRelations.listen((_) => this._fetchCurrentPage()),
            this._sse.onWorker.listen(this._workerListener),
        ];

        // ...and remove event listeners when we leave this route.
        RouteHandle rh = this._rp.route.newHandle();
        rh.onLeave.take(1).listen((e) {
            listeners.forEach((listener) => listener.cancel());
        });
    }

    /// Return relation type as a human-readable string.
    String relType({bool uppercase: false}) {
        String relType;

        if (this._relType == 'friends') {
            relType = 'friends';
        } else {
            relType = 'followers';
        }

        if (uppercase) {
            relType = relType.replaceRange(0, 1, relType[0].toUpperCase());
        }

        return relType;
    }

    /// Listen for updates from background workers.
    void _workerListener(Event e) {
        Map json = JSON.decode(e.data);
        String status = json['status'];

        if (status == 'queued' || status == 'started' || status == 'finished') {
            // This information can only be fetched via REST.
            this._fetchProfileRelationsWorkers();
        } else if (status == 'progress') {
            Map job = this._runningJobs[json['id']];

            if (job != null) {
                // Event contains all the data we need: no need for REST call.
                job['current'] = json['current'];
                job['progress'] = json['progress'];
            } else {
                // This is a job we don't know about: needs REST call.
                this._fetchProfileRelationsWorkers();
            }
        } else if (status == 'failed') {
            this._fetchFailedProfileRelationsTasks().then((_) => this._fetchProfileRelationsWorkers());
        }
    }

    /// Fetch list of relations.
    Future _fetchCurrentPage() {
        Completer completer = new Completer();
        this.error = '';
        this.loading++;
        String pageUrl = '/api/profile/${this.id}/relations/${this._relType}';
        Map urlArgs = {
            'page': this.currentPage,
            'rpp': this._resultsPerPage,
        };

        this.api
            .get(pageUrl, urlArgs: urlArgs, needsAuth: true)
            .then((response) {
                this.siteName = response.data['site_name'];
                this.username = response.data['username'];
                this.relations = new List<Profile>();

                response.data['relations'].forEach((relation) {
                    this.relations.add(new Profile.fromJson(relation));
                });

                this.pager = new Pager(response.data['total_count'],
                                       this.currentPage,
                                       resultsPerPage:this._resultsPerPage);

                this._ts.title = '${this.relType()} by ${this.username}';
                this._updateCrumbs();

                new Future(() {
                    this.scope.broadcast('masonry.layout');
                });
            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {
                this.loading--;
                completer.complete();
            });

        return completer.future;
    }

    /// Request extraction of more friends and follower data for this profile.
    void fetchMoreRelations(Event event, String data, function resetButton) {
        String pageUrl = '/api/profile/${this.id}/relations/fetch';
        this.api
            .get(pageUrl, needsAuth: true)
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {
                resetButton();
            });
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
            new Breadcrumb(this.relType()),
        ];
    }

    /// Fetch worker friends & followers jobs for profile.
    Future _fetchProfileRelationsWorkers() {
        Completer completer = new Completer();

        this.api
            .get('/api/tasks/workers', needsAuth: true)
            .then((response) {
                this.workers = response.data['workers'];
                this.profileRelationsWorkers = [];

                this._runningJobs = new Map<String, Map>();

                this.workers.forEach((worker) {
                    Map currentJob = worker['current_job'];

                    if (currentJob != null) {
                        if (currentJob['profile_id'] == int.parse(this.id)) {
                            if (currentJob['type'] == 'relations') {
                                this._runningJobs[currentJob['id']] = currentJob;
                                this.profileRelationsWorkers.add(worker);

                            }
                        }
                    }
                });
            })
            .whenComplete(() {
                completer.complete();
            });

        return completer.future;
    }

    /// Fetch failed friends and followers task data for this profile.
    Future _fetchFailedProfileRelationsTasks() {
        Completer completer = new Completer();
        List<Map> failed;

        this.api
            .get('/api/tasks/failed', needsAuth: true)
            .then((response) {
                failed = response.data['failed'];
                failed.forEach((failed_task) {
                    if (int.parse(this.id) == failed_task['profile_id']) {
                        if (failed_task['type'] == 'relations') {
                            this.failedTasks = true;
                        }
                    }
                });
                
            })
            .whenComplete(() {
                completer.complete();
            });

        return completer.future;
    }
}
