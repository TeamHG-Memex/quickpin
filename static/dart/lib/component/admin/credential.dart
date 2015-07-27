import 'dart:async';
import 'dart:html';

import 'package:angular/angular.dart';
import 'package:quickpin/authentication.dart';
import 'package:quickpin/component/breadcrumbs.dart';
import 'package:quickpin/component/title.dart';
import 'package:quickpin/rest_api.dart';

/// A component for viewing and modifying credentials.
@Component(
    selector: 'credential-list',
    templateUrl: 'packages/quickpin/component/admin/credential.html',
    useShadowDom: false
)
class CredentialListComponent {
    List<Breadcrumb> crumbs = [
        new Breadcrumb('QuickPin', '/'),
        new Breadcrumb('Administration', '/admin'),
        new Breadcrumb('Credentials'),
    ];

    List<String> allSites = ['instagram', 'twitter'];
    List<String> availableSites = [];
    Map<String,String> credentials;
    String error;
    int loading = 0;
    String newPublic, newSecret, newSite;
    bool showAdd = false;
    List<String> sites;

    final AuthenticationController auth;
    final RestApiController _api;
    final TitleService _ts;

    /// Constructor.
    CredentialListComponent(this.auth, this._api, this._ts) {
        this._fetchCredentials();
        this._ts.title = 'Profiles';
    }

    /// Add the credential represented by this.newSite, this.newPublic, and
    /// this.newSecret.
    void addCredential() {
        this.error = null;
        this.loading++;
        String pageUrl = '/api/credential/${this.newSite}';

        Map body = {
            'public': this.newPublic,
            'secret': this.newSecret,
        };

        this._api
            .put(pageUrl, body, needsAuth: true)
            .then((response) {
                // Insert new site
                this.sites.add(this.newSite);
                this.credentials[this.newSite] = {
                    'public': this.newPublic,
                    'savePublic': (public) => this.updateCredential(this.newSite, public:public),
                    'secret': '********',
                    'saveSecret': (secret) => this.updateCredential(this.newSite, secret:secret),
                };
                this._updateSites();

                // Reset form.
                this.showAdd = false;
                this.newPublic = '';
                this.newSecret = '';
            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {this.loading--;});
    }

    /// Cancel the addition of a new credential.
    void cancelAdd() {
        this.newPublic = '';
        this.newSecret = '';
        this.showAdd = false;
    }

    /// Delete credential for a site.
    void deleteCredential(String site) {
        this.error = null;
        this.loading++;
        String pageUrl = '/api/credential/${site}';

        this._api
            .delete(pageUrl, needsAuth: true)
            .then((response) {
                // Insert new site
                this.sites.remove(site);
                this.credentials.remove(site);
                this._updateSites();
            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {this.loading--;});
    }

    /// Update a credential.
    void updateCredential(String site, {String public, String secret}) {
        this.error = null;
        this.loading++;
        String pageUrl = '/api/credential/${site}';
        Map body = new Map();

        if (public != null) {
            body['public'] = public;
        }

        if (secret != null) {
            body['secret'] = secret;
        }

        this._api
            .put(pageUrl, body, needsAuth: true)
            .then((response) {
                if (public != null) {
                    this.credentials[site]['public'] = public;
                }
            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {this.loading--;});
    }

    /// Fetch a list of credentials.
    void _fetchCredentials() {
        this.error = null;
        this.loading++;
        String pageUrl = '/api/credential/';

        this._api
            .get(pageUrl, needsAuth: true)
            .then(this._handleCredentials)
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {this.loading--;});
    }

    /// Handle the _fetchCredentials XHR response.
    void _handleCredentials(response) {
        this.sites = new List<String>();
        this.credentials = new Map<String,Map>();

        response.data['credentials'].forEach((site,public) {
            this.sites.add(site);
            this.credentials[site] = {
                'public': public,
                'savePublic': (public) => this.updateCredential(site, public:public),
                'secret': '********',
                'saveSecret': (secret) => this.updateCredential(site, secret:secret),
            };
        });

        this._updateSites();
    }

    /// Update internal site representations.
    ///
    /// This must always be called after adding or removing items from
    /// this.credentials.
    void _updateSites() {
        this.sites.sort();
        this.availableSites = new List<String>();

        this.allSites.forEach((site) {
            if (!this.sites.contains(site)) {
                this.availableSites.add(site);
            }
        });

        this.availableSites.sort();
        this.newSite = this.availableSites[0];
    }
}
