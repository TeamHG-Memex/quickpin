import 'dart:convert';
import 'dart:html';

import 'package:angular/angular.dart';
import 'package:quickpin/authentication.dart';
import 'package:quickpin/component/title.dart';
import 'package:quickpin/rest_api.dart';

/// A controller that presents a UI for logging in.
@Component(
    selector: 'login',
    templateUrl: 'packages/quickpin/component/login.html',
    useShadowDom: false
)
class LoginComponent {
    AuthenticationController auth;
    RestApiController server;
    RouteProvider rp;
    TitleService ts;

    String email='', password='', error='';
    bool buttonBusy = false;

    /// Constructor.
    LoginComponent(this.auth, this.rp, this.server, this.ts) {
        this.ts.title = 'Login';

        if (this.rp.route.queryParameters['expired'] == 'true') {
            this.error = 'Your session has expired. Please log in again'
                         ' to continue.';
        }
    }

    /// Ask the server to validate the user's credentials and give us an
    /// authentication token for future API requests.
    ///
    /// We don't want to use the rest_api.dart methods here, because those
    /// will try to redirect us to login, but we're already at login!
    void login() {
        this.buttonBusy = true;
        var request = new HttpRequest();

        // Create request.
        var responseHandler = (_) {
            var response = new ApiResponse(request.status, request.response);

            if (request.status == 200) {
                this.error = '';
                this.auth.checkToken(response.data['token']);
            } else {
                this.error = response.data['message'];
                this.buttonBusy = false;
            }
        };

        request.onLoadEnd.listen(responseHandler);
        request.onError.listen(responseHandler);
        request.open('POST', '/api/authentication/', async:true);
        request.setRequestHeader('Accept', 'application/json');
        request.setRequestHeader('Content-Type', 'application/json');

        String payload = JSON.encode({
            'email': this.email,
            'password': this.password
        });

        request.send(payload);
    }
}
