import 'package:angular/angular.dart';
import 'package:quickpin/authentication.dart';
import 'package:quickpin/redirect.dart';

/// Configures routes for the application.
@Injectable()
class QuickPinRouteInitializer implements Function {
    AuthenticationController auth;

    QuickPinRouteInitializer(this.auth);

    /// Configures routes for the application.
    ///
    /// Although the router allows hierarchical routes, we opted for "flat"
    /// routes based on discussion on GitHub:
    /// https://github.com/angular/route.dart/issues/69#issuecomment-81612794
    void call(Router router, RouteViewFactory views) {
        views.configure({
            'admin': ngRoute(
                path: '/admin',
                preEnter: auth.requireLogin,
                viewHtml: '<admin-index></admin-index>'
            ),
            'background_tasks': ngRoute(
                path: '/admin/background-tasks',
                preEnter: auth.requireLogin,
                viewHtml: '<background-tasks></background-tasks>'
            ),
            'credentials': ngRoute(
                path: '/admin/credential',
                preEnter: auth.requireLogin,
                viewHtml: '<credential-list></credential-list>'
            ),
            'home': ngRoute(
                path: '/',
                preEnter: auth.requireLogin,
                viewHtml: '<home></home>'
            ),
            'login': ngRoute(
                path: '/login',
                preEnter: auth.requireNoLogin,
                viewHtml: '<login></login>'
            ),
            'redirect': ngRoute(
                path: '/redirect/:url',
                preEnter: redirect
            ),
            'search': ngRoute(
                path: '/search',
                preEnter: auth.requireLogin,
                dontLeaveOnParamChanges: true,
                viewHtml: '<search></search>'
            ),
            'profile_list': ngRoute(
                path: '/profile',
                preEnter: auth.requireLogin,
                dontLeaveOnParamChanges: true,
                viewHtml: '<profile-list></profile-list>'
            ),
            'profile_view': ngRoute(
                path: '/profile/:id',
                preEnter: auth.requireLogin,
                dontLeaveOnParamChanges: true,
                viewHtml: '<profile></profile>'
            ),
            'user_list': ngRoute(
                path: '/user',
                preEnter: auth.requireLogin,
                dontLeaveOnParamChanges: true,
                viewHtml: '<user-list></user-list>'
            ),
            'user_view':ngRoute(
                path: '/user/:id',
                preEnter: auth.requireLogin,
                viewHtml: '<user></user>'
            ),

        });
    }
}

