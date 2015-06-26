library subject_view;

import 'package:angular/angular.dart';
import 'dart:html';

@Component(selector: 'subject-view', templateUrl: 'packages/quickpin/component/subject-view.html', cssUrl: 'subject-view.css', useShadowDom: false)
class SubjectViewComponent {
  Map subject;
  final Http _http;
  String newNote;
  Map newField = {'key': '', 'value': ''};
  bool savingNotes;
  bool savingFields;

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

  void addNote() {
    subject['notes'] = (subject['notes'] is List) ? subject['notes'] : [];
    subject['notes'].add(newNote);
    savingNotes = true;
    _http.post('/api/subject/${subject['_id']}', {'notes': subject['notes']}).then((HttpResponse response) {
      savingNotes = false;
      if (response.data["success"]) {
        newNote = '';
      } else {
        subject['notes'].remove(newNote);
        window.console.error(response.data);
      }
    });
  }

  void removeNote(String note) {
    subject['notes'].remove(note);
    savingNotes = true;
    _http.post('/api/subject/${subject['_id']}', {'notes': subject['notes']}).then((HttpResponse response) {
      savingNotes = false;
      if (response.data["success"]) {} else {
        subject['notes'].add(note);
        window.console.error(response.data);
      }
    });
  }

  void addField() {
    subject['fields'] = (subject['fields'] is List) ? subject['fields'] : [];
    subject['fields'].add(newField);
    savingFields = true;
    _http.post('/api/subject/${subject['_id']}', {'fields': subject['fields']}).then((HttpResponse response) {
      savingFields = false;
      if (response.data["success"]) {
        newField = {'key': '', 'value': ''};
      } else {
        subject['fields'].remove(newField);
        window.console.error(response.data);
      }
    });
  }

  void removeField(Map field) {
    subject['fields'].remove(field);
    savingFields = true;
    _http.post('/api/subject/${subject['_id']}', {'fields': subject['fields']}).then((HttpResponse response) {
      savingFields = false;
      if (response.data["success"]) {} else {
        subject['fields'].add(field);
        window.console.error(response.data);
      }
    });
  }

  int calculateFollowingPercentage() {
    if (subject == null) { return 50; }
    RegExp dotcomma = new RegExp(r'[.,]');
    int friends = int.parse(subject['twitter']['followingCount'].replaceAll(dotcomma, ''));
    int followers = int.parse(subject['twitter']['followerCount'].replaceAll(dotcomma, ''));
    int total = friends + followers;
    if (total > 0) {
      return (100 * followers / total).round();
    }
    return 50;
  }
}
