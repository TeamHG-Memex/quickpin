library subject_search_box;

import 'package:angular/angular.dart';

@Component(
    selector: 'subject-search-box', templateUrl: 'packages/quickpin/component/subject-search-box.html', cssUrl: 'subject-search-box.css', useShadowDom: false)
class SubjectSearchBoxComponent {
  @NgTwoWay('show-all')
  bool showAll;

  @NgTwoWay('filter-text')
  String filterText;
}
