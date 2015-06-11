library quickpin_layout;

import 'package:angular/angular.dart';

@Component(selector: 'quick-pin', templateUrl: 'packages/quickpin/component/quick-pin.html', cssUrl: 'quick-pin.css', useShadowDom: false)
class QuickPinComponent {
  String filterText;
  bool showAll;
  List<Map> subjects;
  final Http _http;

  QuickPinComponent(this._http) {
    showAll = false;
    filterText = '';
    _http.get('/api/subject').then((HttpResponse response) {
      subjects = response.data;
    });
  }
}
