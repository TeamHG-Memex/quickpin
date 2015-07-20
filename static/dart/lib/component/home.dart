import 'dart:async';
import 'dart:convert';
import 'dart:html';

import 'package:angular/angular.dart';
import 'package:quickpin/component/title.dart';
import 'package:quickpin/mixin/sort.dart';
import 'package:quickpin/rest_api.dart';

/// The home view.
@Component(
    selector: 'home',
    templateUrl: 'packages/quickpin/component/home.html',
    useShadowDom: false
)
class HomeComponent extends Object {
    RestApiController _api;
    RouteProvider _rp;
    TitleService _ts;

    bool loadingOverall = false,
         loadingSites = false,
         loadingUsers = false;

    List<DarkUser> users;
    List<DarkSite> sites;
    List<Map> overallStats;

    String siteSortColumn = 'posts';
    String userSortColumn = 'posts';

    /// Constructor.
    HomeComponent(this._api, this._rp, this._ts) {
        this._fetchUsers()
            .then((_) => this._fetchSites())
            .then((_) => this._fetchOverall());

        this._ts.title = 'Home';
    }

    /// Change the current sort column for sites.
    void sortSites(String sortColumn) {
        if (this.siteSortColumn != sortColumn) {
            this.siteSortColumn = sortColumn;
            this._fetchSites();
        }
    }

    /// Change the current sort column for users.
    void sortUsers(String sortColumn) {
        if (this.userSortColumn != sortColumn) {
            this.userSortColumn = sortColumn;
            this._fetchUsers();
        }
    }

    /// Get overall statistics from the API.
    Future _fetchOverall() {
        Completer completer = new Completer();
        this.loadingOverall = true;

        this._api
            .get('/api/statistics/overall', needsAuth: true)
            .then((response) {
                Map result = response.data;

                this.overallStats = [
                    {
                        'name': 'Total Chat Messages',
                        'value': result['chat_count']
                    },
                    {
                        'name': 'Total Forum Posts',
                        'value': result['post_count']
                    },
                    {
                        'name': 'Total Images',
                        'value': result['image_count']
                    },
                    {
                        'name': 'Total Private Messages (PMs)',
                        'value': result['pm_count']
                    },
                    {
                        'name': 'Total Users',
                        'value': result['user_count']
                    },
                    {
                        'name': 'Total Web Sites',
                        'value': result['site_count']
                    },
                ];
            })
            .whenComplete(() {
                completer.complete();
                this.loadingOverall = false;
            });

        return completer.future;
    }

    /// Get site data from API.
    Future _fetchSites() {
        Completer completer = new Completer();
        this.loadingSites = true;
        Map urlArgs = {
            'page': 1,
            'rpp': 10,
            'sort': '-' + this.siteSortColumn,
        };

        this._api
            .get('/api/dark-site/', urlArgs: urlArgs, needsAuth: true)
            .then((response) {
                this.sites = new List<DarkSite>();

                response.data['sites'].forEach((jsonSite) {
                    this.sites.add(new DarkSite.fromJson(jsonSite));
                });
            })
            .whenComplete(() {
                completer.complete();
                this.loadingSites = false;
            });

        return completer.future;
    }

    /// Get user data from API.
    Future _fetchUsers() {
        Completer completer = new Completer();
        this.loadingUsers = true;
        Map urlArgs = {
            'page': 1,
            'rpp': 10,
            'sort': '-' + this.userSortColumn,
        };

        this._api
            .get('/api/dark-user/', urlArgs: urlArgs, needsAuth: true)
            .then((response) {
                this.users = new List<DarkUser>();

                response.data['users'].forEach((jsonUser) {
                    this.users.add(new DarkUser.fromJson(jsonUser));
                });
            }).whenComplete(() {
                completer.complete();
                this.loadingUsers = false;
            });

        return completer.future;
    }
}
