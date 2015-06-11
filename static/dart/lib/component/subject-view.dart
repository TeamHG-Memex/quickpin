library subject_view;

import 'package:angular/angular.dart';

@Component(selector: 'subject-view', templateUrl: 'packages/quickpin/component/subject-view.html', cssUrl: 'subject-view.css', useShadowDom: false)
class SubjectViewComponent {
  Map subject;
  final Http _http;
  SubjectViewComponent(this._http, RouteProvider route) {
    String username = route.parameters['username'];
    if (username != null) {
      _http.get('/api/subject/byUsername/${username}').then((HttpResponse response) {
        subject = response.data;
      });
    }

    String oid = route.parameters['oid'];
    if (oid != null) {
      _http.get('/api/subject/${oid}').then((HttpResponse response) {
        subject = response.data;
      });
    }
  }
}
