library quickpin_router;

import 'package:angular/angular.dart';

void QuickPinRouter(Router router, RouteViewFactory views) {
  views.configure({
    'index': ngRoute(defaultRoute: true, enter: (_) => router.go('subject', {})),
    'subject': ngRoute(
        path: '/subject',
        mount: {
      'index': ngRoute(defaultRoute: true, enter: (_) => router.go('subject.list', {})),
      'list': ngRoute(path: '/list', view: 'web/view/subject/list.html'),
      'add': ngRoute(path: '/add', view: 'web/view/subject/add.html'),
    }),
  });
}
