library subject_grid;

import 'package:angular/angular.dart';

@Component(selector: 'subject-grid', templateUrl: 'packages/quickpin/component/subject-grid.html', cssUrl: 'subject-grid.css', useShadowDom: false)
class SubjectGridComponent {
  @NgTwoWay('show-all')
  bool showAll;

  @NgTwoWay('filter-text')
  String filterText;

  @NgTwoWay('subjects')
  List<Map> subjects;
}
