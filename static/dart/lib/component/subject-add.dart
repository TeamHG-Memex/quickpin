library subject_add;

import 'package:angular/angular.dart';
import 'dart:html';

@Component(selector: 'subject-add', templateUrl: 'packages/quickpin/component/subject-add.html', cssUrl: 'subject-add.css', useShadowDom: false)
class SubjectAddComponent {
  String screenNames;
  final Http _http;
  bool saving;

  SubjectAddComponent(this._http) {}

  void addSubjects() {
    saving = true;
    _http.put('/api/subject/', screenNames).then((HttpResponse response) {
      if (response.data['success']) {
        screenNames = "";
        saving = false;
      } else {
        window.console.error(response.data);
      }
    });
  }
}
