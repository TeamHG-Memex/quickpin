import 'dart:async';
import 'dart:html';

import 'package:angular/angular.dart';
import 'package:quickpin/component/breadcrumbs.dart';
import 'package:quickpin/component/title.dart';
import 'package:quickpin/rest_api.dart';
import 'package:quickpin/sse.dart';

/// A controller for administering the application.
@Component(
    selector: 'background-tasks',
    templateUrl: 'packages/quickpin/component/admin/background_tasks.html',
    useShadowDom: false
)
class BackgroundTasksComponent {
    List<Breadcrumb> crumbs = [
        new Breadcrumb('QuickPin', '/'),
        new Breadcrumb('Background Tasks'),
    ];

    bool loadingFailedTasks = false;
    bool loadingQueues = false;
    bool loadingWorkers = false;
    List<Map> failed;
    List<Map> queues;
    List<Map> workers;

    final RestApiController _api;
    final RouteProvider _rp;
    final SseController _sse;
    final TitleService _ts;

    /// Constructor.
    BackgroundTasksComponent(this._api, this._rp, this._sse, this._ts) {
        this._fetchWorkers();
        this._fetchQueues();
        this._fetchFailedTasks();
        this._ts.title = 'Background Tasks';

        // This is ported from Avatar, where we have long running tasks. We
        // don't need it in QuickPin (yet) so it's commented out. When
        // re-enabled, it should be ported to use SSE instead of polling.
        // Timer refresh = new Timer.periodic(
        //     new Duration(seconds: 3),
        //     (_) => this._fetchWorkers()
        // );

        // Clean up the timer when we leave the route.
        RouteHandle rh = this._rp.route.newHandle();
        StreamSubscription subscription = rh.onLeave.take(1).listen((e) {
            refresh.cancel();
        });
    }

    /// Handle a button press to remove a single task.
    void removeFailedTask(Event event, String taskId, Function resetButton) {
        this._api
            .delete('/api/tasks/failed/$taskId', needsAuth: true)
            .then((response) {
                for (int i = 0; i < this.failed.length; i++) {
                    if (this.failed[i]['id'] == taskId) {
                        this.failed.removeAt(i);
                        break;
                    }
                }
            })
            .whenComplete(resetButton);
    }

    /// Fetch failed task data.
    void _fetchFailedTasks() {
        this.loadingFailedTasks = true;

        this._api
            .get('/api/tasks/failed', needsAuth: true)
            .then((response) {this.failed = response.data['failed'];})
            .whenComplete(() {this.loadingFailedTasks = false;});
    }

    /// Fetch queue data.
    void _fetchQueues() {
        this.loadingQueues = true;

        this._api
            .get('/api/tasks/queues', needsAuth: true)
            .then((response) {this.queues = response.data['queues'];})
            .whenComplete(() {this.loadingQueues = false;});
    }

    /// Fetch worker data.
    void _fetchWorkers() {
        this.loadingWorkers = true;

        this._api
            .get('/api/tasks/workers', needsAuth: true)
            .then((response) {this.workers = response.data['workers'];})
            .whenComplete(() {this.loadingWorkers = false;});
    }
}
