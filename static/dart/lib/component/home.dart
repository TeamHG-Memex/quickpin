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

    /// Constructor.
    HomeComponent(this._api, this._rp, this._ts) {
        this._ts.title = 'Home';
    }
}
