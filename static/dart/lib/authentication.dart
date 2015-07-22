import 'dart:async';
import 'dart:convert';
import 'dart:html';

import 'package:angular/angular.dart';
import 'package:quickpin/model/user.dart';
import 'package:quickpin/rest_api.dart';

/// Handles authentication and access control.
@Injectable()
class AuthenticationController {
    User currentUser;
    String token;

    Router _router;
    String _stashedUrl;

    Completer<bool> _loggedInCompleter;
    Completer<bool> _notLoggedInCompleter;

    /// Constructor.
    AuthenticationController(this._router) {
        this._initCompleters();

        if (window.localStorage.containsKey('token')) {
            var tokenFuture = this._verifyToken(window.localStorage['token']);
            this._loggedInCompleter.complete(tokenFuture);
        } else {
            this._loggedInCompleter.complete(false);
        }
    }

    /// Check if a token is valid. Returns a future.
    Future checkToken(String token) {
        this._initCompleters();

        var tokenFuture = this._verifyToken(token, redirect: true);
        this._loggedInCompleter.complete(tokenFuture);
        return tokenFuture;
    }

    /// Returns true if the user is an admin.
    bool isAdmin() {
        return isLoggedIn() && currentUser.isAdmin;
    }

    /// Returns true if the user is logged in.
    bool isLoggedIn() {
        return currentUser != null;
    }

    /// Clear out the user's authentication status.
    ///
    /// Note that this purely modifies the client state; no interaction with
    /// the server is required.
    void logOut({expired: false}) {
        this.currentUser = null;
        this.token = null;


        this._initCompleters();
        this._loggedInCompleter.complete(false);

        Map loginArgs = {};

        if (expired) {
            this._stashedUrl = window.location.pathname;
            loginArgs['expired'] = 'true';
        }

        this._router.go('login', {}, queryParameters:loginArgs);
    }

    /// This decorator marks a route as requiring a logged in user.
    void requireLogin(RoutePreEnterEvent e) {
        e.allowEnter(this._loggedInCompleter.future);

        this._loggedInCompleter.future.then((result) {
            if (!result) {
                this._stashedUrl = window.location.pathname;
                this._router.go('login', {});
            }
        });
    }

    /// This decorator marks a route as requiring a NOT logged in user.
    ///
    /// This is intended for views like the login screen, which we do not
    /// want to show to a user that is already logged in.
    ///
    /// Note that we introduce a second completer (_notLoggedInCompleter)
    /// because it needs to return the opposite result as _loggedInCompleter,
    /// and there's no direct way to negate a future.
    void requireNoLogin(RoutePreEnterEvent e) {
        e.allowEnter(this._notLoggedInCompleter.future);

        this._notLoggedInCompleter.future.then((result) {
            if (!result && this._router.activePath.length == 0) {
                this._router.go('home', {});
            }
        });
    }

    /// Processes the server's authentication response.
    void _continueVerifyToken(HttpRequest request, Completer tokenCompleter) {
        Map json = JSON.decode(request.response);

        if (json['email'] != null) {
            this.currentUser = new User(json['id'], json['email'], json['is_admin']);
            tokenCompleter.complete(true);

            // Try to load a complete user profile.
            HttpRequest.request(
                json['url'],
                requestHeaders: {
                    'Accept': 'application/json',
                    'X-Auth': this.token,
                }
            ).then((request) {
                Map innerJson = JSON.decode(request.response);
                this.currentUser = new User.fromJson(innerJson);
            });

        } else {
            tokenCompleter.complete(false);
        }
    }

    /// Sets up the intial authentication state.
    ///
    /// When the page first loads, we don't know if the user is logged in or
    /// not until we get the result of an authentication XHR. This method
    /// handles the future result of that XHR.
    void _initCompleters() {
        this._loggedInCompleter = new Completer<bool>();
        this._notLoggedInCompleter = new Completer<bool>();

        this._loggedInCompleter.future.then((isLoggedIn) {
            // Remove loading screen, if it exists.
            var loadingDiv = document.getElementById('loading-screen');

            if (loadingDiv != null) {
                loadingDiv.remove();
            }

            // Clear the token if the user is not logged in.
            if (!isLoggedIn && window.localStorage.containsKey('token')) {
                window.localStorage.remove('token');
            }

            // The result of _notLoggedInCompleter is the opposite of
            // _loggedInCompleter.
            this._notLoggedInCompleter.complete(!isLoggedIn);
        });
    }

    /// Redirect the user to a stashed URL.
    void _redirect(bool verified) {
        if (verified) {
            if (this._stashedUrl == null) {
                this._router.go('home', {});
            } else {
                this._router.gotoUrl(this._stashedUrl);
                this._stashedUrl = null;
            }
        }
    }

    /// Attempt to authenticate a user with the specified authentication token.
    ///
    /// This triggers an XHR to verify the authentication credentials and
    /// returns a future that resolves succesfully when the token is verified
    /// or resolves with an error if a failure occurs during token verification.
    Future _verifyToken(String token, {bool redirect: false}) {
        this.token = token;
        window.localStorage['token'] = token;
        var tokenCompleter = new Completer();

        // We can't use the RestApiController class here because it has a
        // dependency on this class, and circular dependencies aren't allowed.
        HttpRequest.request(
            '/api/authentication/',
            requestHeaders: {
                'Accept': 'application/json',
                'X-Auth': this.token,
            }
        ).then((request) {
            this._continueVerifyToken(request, tokenCompleter);
        }).catchError((e) {
            tokenCompleter.complete(false);
        });

        if (redirect == true) {
            tokenCompleter.future.then(this._redirect);
        }

        return tokenCompleter.future;
    }
}
