library subject_grid;

import 'package:angular/angular.dart';
import 'dart:html';

@Component(selector: 'subject-grid', templateUrl: 'packages/quickpin/component/subject-grid.html', cssUrl: 'subject-grid.css', useShadowDom: false)
class SubjectGridComponent {
  @NgTwoWay('show-all')
  bool showAll;

  @NgTwoWay('filter-text')
  String filterText;

  @NgTwoWay('subjects')
  List<Map> subjects;

  final Http _http;

  SubjectGridComponent(this._http) {
    _http.get('/api/subject').then((HttpResponse response) {
      subjects = response.data;
    });
  }

  void toggleTrack(subject) {
    String newStatus = (subject['status'] == 'tracked') ? 'ignored' : 'tracked';
    _http.post('/api/subject/${subject['_id']}', {'status': newStatus}).then((HttpResponse response) {
      if (response.data["success"]) {
        subject['status'] = newStatus;
      } else {
        window.console.error(response.data);
      }
    });
  }
}
