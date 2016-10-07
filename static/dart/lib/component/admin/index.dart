import 'dart:async';
import 'dart:html';

import 'package:angular/angular.dart';
import 'package:quickpin/authentication.dart';
import 'package:quickpin/component/breadcrumbs.dart';
import 'package:quickpin/component/title.dart';
import 'package:quickpin/rest_api.dart';

/// A component for viewing and modifying credentials.
@Component(
    selector: 'admin-index',
    templateUrl: 'packages/quickpin/component/admin/index.html',
    useShadowDom: false
)
class AdminIndexComponent {
    List<Breadcrumb> crumbs = [
        new Breadcrumb('QuickPin', '/'),
        new Breadcrumb('Administration'),
    ];

    final TitleService _ts;

    /// Constructor.
    AdminIndexComponent(this._ts) {
        this._ts.title = 'Administration';
    }
}
