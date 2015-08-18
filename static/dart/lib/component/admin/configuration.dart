import 'dart:async';
import 'dart:html';

import 'package:angular/angular.dart';
import 'package:quickpin/authentication.dart';
import 'package:quickpin/component/breadcrumbs.dart';
import 'package:quickpin/component/title.dart';
import 'package:quickpin/rest_api.dart';

/// A component for viewing and modifying credentials.
@Component(
    selector: 'configuration-list',
    templateUrl: 'packages/quickpin/component/admin/configuration.html',
    useShadowDom: false
)
class ConfigurationListComponent {
    List<Breadcrumb> crumbs = [
        new Breadcrumb('QuickPin', '/'),
        new Breadcrumb('Administration', '/admin'),
        new Breadcrumb('Configuration'),
    ];

    List<String> keys;
    Map<String,Map> configuration;
    String error;
    int loading = 0;

    final AuthenticationController auth;
    final RestApiController _api;
    final TitleService _ts;

    /// Constructor.
    ConfigurationListComponent(this.auth, this._api, this._ts) {
        this._fetchConfiguration();
        this._ts.title = 'Configuration';
    }

    /// Fetch a list of configuration key/value pairs.
    void _fetchConfiguration() {
        this.error = null;
        this.loading++;
        String pageUrl = '/api/configuration/';

        this._api
            .get(pageUrl, needsAuth: true)
            .then((response) {
                this.configuration = new Map<String,Map>();

                response.data['configuration'].forEach((key, value) {
                    this.configuration[key] = {
                        'value': value,
                        'save': (v) => this._updateConfiguration(key, v),
                    };
                });

                this.keys = new List<String>.from(this.configuration.keys);
                this.keys.sort();

                window.console.log(this.keys);
            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {this.loading--;});
    }

    /// Update a configuration item.
    void _updateConfiguration(String key, String value) {
        this.error = null;
        this.loading++;
        String pageUrl = '/api/configuration/${key}';
        Map body = {'value': value};

        this._api
            .put(pageUrl, body, needsAuth: true)
            .then((response) {
                this.configuration[key]['value'] = value;
            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {this.loading--;});
    }
}
