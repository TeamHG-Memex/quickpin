import 'dart:async';
import 'dart:html';
import 'dart:convert';

import 'package:angular/angular.dart';
import 'package:quickpin/authentication.dart';
import 'package:quickpin/query_watcher.dart';
import 'package:quickpin/component/breadcrumbs.dart';
import 'package:quickpin/component/pager.dart';
import 'package:quickpin/component/title.dart';
import 'package:quickpin/model/note.dart';
import 'package:quickpin/rest_api.dart';
import 'package:quickpin/sse.dart';

/// A component for notes by a specified profile.
@Component(
    selector: 'profile-notes',
    templateUrl: 'packages/quickpin/component/profile/notes.html',
    useShadowDom: false
)
class ProfileNotesComponent extends Object
                            implements ScopeAware {
    AuthenticationController auth;
    List<Breadcrumb> crumbs;

    String error = '';
    String id;
    int loading = 0;
    Pager pager;
    List<Note> notes;
    Scope scope;
    String username;
    String siteName;
    String noteError;
    int editingNoteId;
    int deletingNoteId;
    String newLabelText;
    String newNoteBody;
    String newNoteCategory;
    Map<int, Note> noteIdMap;
    List<int> noteIds;
    QueryWatcher _queryWatcher;

    final RestApiController api;

    final RouteProvider _rp;
    final TitleService _ts;
    final SseController _sse;

    /// Constructor.
    ProfileNotesComponent(this.api, this.auth, this._rp, this._sse, this._ts) {
        this.id = this._rp.parameters['id'];
        this._ts.title = 'Notes by ${id}';
        this._updateCrumbs();
        RouteHandle rh = this._rp.route.newHandle();

        this._queryWatcher = new QueryWatcher(
            rh,
            ['page', 'rpp'],
            this._fetchCurrentPage
        );

        // Add event listeners...
        List<StreamSubscription> listeners = [
            this._sse.onProfileNotes.listen((_) => this._fetchCurrentPage()),
        ];

        // ...and remove event listeners when we leave this route.
        UnsubOnRouteLeave(rh, [
            this._sse.onProfileNotes.listen(this._fetchCurrentPage),
        ]);

        this._fetchCurrentPage();
    }

    /// Update breadcrumbs.
    void _updateCrumbs() {

        this.crumbs = [
            new Breadcrumb('QuickPin', '/'),
            new Breadcrumb('Profile', '/profile'),
            new Breadcrumb(this.username, '/profile/${this.id}'),
            new Breadcrumb('Notes'),
        ];
    }


    /// Fetch list of notes.
    Future _fetchCurrentPage() {
        Completer completer = new Completer();
        this.noteIdMap = new Map<int, Note>();
        this.noteIds = new List<int>();
        this.error = '';
        this.loading++;
        String profileUrl = '/api/profile/${this.id}/notes';
        Map urlArgs = {
            'page': this._queryWatcher['page'] ?? '1',
            'rpp': this._queryWatcher['rpp'] ?? '10',
        };

        this.api
            .get(profileUrl, urlArgs: urlArgs, needsAuth: true)
            .then((response) {
                this.notes = new List<ProfileNote>();
                this.siteName = response.data['site_name'];
                this.username = response.data['username'];
                response.data['notes'].forEach((note) {
                    this.notes.add(new Note.fromJson(note));
                    this.noteIdMap[note['id']] = new Note.fromJson(note);
                });
                this.noteIds = this.noteIdMap.keys.toList();

                this.pager = new Pager(response.data['total_count'],
                                       int.parse(this._queryWatcher['page'] ?? '1'),
                                       resultsPerPage:int.parse(this._queryWatcher['rpp'] ?? '10'));

                this._ts.title = 'Notes for ${this.username}';
                this._updateCrumbs();
            })
            .catchError((response) {
                this.error = response.data['message'];
            })
            .whenComplete(() {
                this.loading--;
                completer.complete();
            });

        return completer.future;
    }

    /// Get a query parameter as an int.
    void _getQPInt(value, [defaultValue]) {
        if (value != null) {
            return int.parse(value);
        } else {
            return defaultValue;
        }
    }

    /// Get a query parameter as a string.
    void _getQPString(value, [defaultValue]) {
        if (value != null) {
            return Uri.decodeComponent(value);
        } else {
            return defaultValue;
        }
    }

    void editNote(int noteId) {
        Note note = this.noteIdMap[noteId];
        this.newNoteCategory = note.category;
        this.newNoteBody = note.body;
        this.editingNoteId = noteId;

    }

    void deleteNote(int noteId) {
        this.deletingNoteId = noteId;
    }

    // Edit a profile note. 
    void editProfileNote(Event event, dynamic data, Function resetButton) {
        this.noteError = null;
        Map note = null;
       
        if (this.newNoteCategory == null || this.newNoteBody == null) {
            this.noteError = 'You must enter category and text for the label.';
        } else {
            this.loading++;
            String noteUrl = '/api/note/${this.editingNoteid}';
            note = {
                'category': this.newNoteCategory,
                'body': this.newNoteBody,
                'profile_id': this.id,
            };
            bool success = true;
            this.api
                .put(noteUrl, note, needsAuth: true)
                .then((response) {
                })
                .catchError((response) {
                    this.noteError = response.data['message'];
                    success = false;
                })
                .whenComplete(() {
                    this.loading--;
                    if (success) {
                        this.newNoteCategory = null;
                        this.newNoteBody = null;
                        this.editingNoteId = null;
                        Modal.wire($("#edit-note-modal")).hide();
                    }
                });
        }
        resetButton();
    }

    void deleteProfileNote(Event event, dynamic data, Function resetButton) {
        this.noteError = null;
        Map note = null;
       
        this.loading++;
        String noteUrl = '/api/note/${this.deletingNoteId.toString()}';
        bool success = true;
        this.api
            .delete(noteUrl, needsAuth: true)
            .then((response) {
            })
            .catchError((response) {
                this.noteError = response.data['message'];
                success = false;
            })
            .whenComplete(() {
                this.loading--;
                if (success) {
                    this.newNoteCategory = null;
                    this.newNoteBody = null;
                    this.editingNoteId = null;
                    Modal.wire($("#delete-note-modal")).hide();
                }
            });
        resetButton();
    }
}
