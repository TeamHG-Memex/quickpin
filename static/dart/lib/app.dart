library quickpin_app;

import 'package:angular/angular.dart';

// import components here
import 'package:quickpin/component/subject-search-box.dart';
import 'package:quickpin/component/subject-grid.dart';
import 'package:quickpin/component/subject-add.dart';
import 'package:quickpin/component/nav-bar.dart';
import 'package:quickpin/component/quick-pin.dart';

import 'router.dart';

class QuickPin extends Module {
  QuickPin() {
    // bind components here
    bind(SubjectSearchBoxComponent);
    bind(SubjectGridComponent);
    bind(SubjectAddComponent);
    bind(NavBarComponent);
    bind(QuickPinComponent);

    bind(RouteInitializerFn, toValue: QuickPinRouter);
    bind(NgRoutingUsePushState, toValue: new NgRoutingUsePushState.value(false));
  }
}
