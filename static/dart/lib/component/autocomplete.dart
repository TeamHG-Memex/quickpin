import 'dart:async';
import 'dart:html';

import 'package:angular/angular.dart';
import 'package:quickpin/rest_api.dart';

/// A component for autocompleting a text field.
@Component(
    selector: 'autocomplete',
    templateUrl: 'packages/quickpin/component/autocomplete.html',
    useShadowDom: false
)
class AutocompleteComponent {
    @NgOneWay('data')
    AutocompleteData data;

    @NgOneWay('data-source')
    Function dataSource;

    @NgAttr('placeholder')
    Function placeholder;

    @NgAttr('size')
    int size;

    int highlightIndex;
    int loading = 0;
    AutocompleteData results;

    Element _element;

    /// Constructor.
    AutocompleteComponent(this._element) {
        this._element.attributes['custom-form'] = '';
        // This will get overwritten if the 'data-source' attribute is supplied.
        this.dataSource = this._defaultDataSource;
        this._element.addEventListener('reset', (_) => this.reset());
    }

    /// Cancel selection.
    ///
    /// Delay just a bit before clearing the autocomplete value: if the user
    /// clicked another option, the blur event is emitted before the click
    /// event, so cancel() won't see the new value right away.
    void cancel(Event event) {
        new Timer(new Duration(milliseconds:200), () {
            this.results = null;

            if (this._element.attributes['custom-form'] == null) {
                this._element.querySelector('input').value = '';
            }
        });
    }

    /// Higlight the completion item at ``index``.
    void highlight(int index) {
        this.highlightIndex = index;
    }

    /// Handle keyboad events in the input field.
    void handleKeyUp(KeyboardEvent event) {
        if (event.keyCode == KeyCode.UP) {
            if (this.highlightIndex == null || this.highlightIndex <= 0) {
                this.highlightIndex = null;
            } else {
                this.highlightIndex--;
            }
            event.stopPropagation();
        } else if (event.keyCode == KeyCode.DOWN) {
            if (this.highlightIndex == null) {
                this.highlightIndex = 0;
            } else if (this.results != null &&
                       this.highlightIndex < this.results.list.length - 1) {
                this.highlightIndex++;
            }
            event.stopPropagation();
        } else if (event.keyCode == KeyCode.ENTER && this.results != null) {
            this.select(event, this.results.list[this.highlightIndex]);
            event.stopPropagation();
        } else if (event.keyCode == KeyCode.ESC) {
            this.highlightIndex = null;
            this.results = null;
            event.stopPropagation();
        } else {
            this.highlightIndex = null;
            showCompletions(event);
        }
    }

    /// Ignore arrow keys and enter.
    void ignoreArrows(Event event) {
        if (event.keyCode == KeyCode.UP ||
            event.keyCode == KeyCode.DOWN ||
            event.keyCode == KeyCode.ENTER) {

            event.preventDefault();
            event.stopPropagation();
        }
    }

    /// Select an autocomplete item.
    void select(Event event, AutocompleteDatum datum) {
        this.results = null;
        this._element.attributes['custom-form'] = datum.id;
        this._element.querySelector('input').value = datum.label;
        event.stopPropagation();
    }

    /// Show the list of possible completions.
    void showCompletions(Event event) {
        String query = event.target.value.toLowerCase();
        this._element.attributes['custom-form'] = '';

        if (query.trim() == '') {
            this.results = null;
        } else {
            this.loading++;
            this.dataSource(query).then((AutocompleteData results) {
                this.results = results;
            })
            .whenComplete(() {
                this.loading--;
            });
        }
    }

    /// Reset the autocomplete input.
    void reset() {
        this.results = null;
        this._element.attributes['custom-form'] = '';
        this._element.querySelector('input').value = '';
    }

    /// This is a default implementation of a dataSource. It does a
    /// case-insensitive, prefix comparison against ``data``.
    Future<AutocompleteData> _defaultDataSource(String query) {
        if (this.data == null) {
            throw new Exception('`data` should not be null.');
        }

        AutocompleteData results = new AutocompleteData();

        this.data.list.forEach((datum) {
            if (datum.label.toLowerCase().startsWith(query)) {
                results.list.add(datum);
            }
        });

        return new Future.value(results);
    }

    //// Fetch completion data from API.
    void _fetchData() {
        loading++;
    }
}

/// A single autocomplete item.
class AutocompleteDatum {
    String id;
    String label;
    var extra;

    AutocompleteDatum.fromJson(Map json) {
        if (json['id'] == null || json['label'] == null) {
            throw new Exception('Invalid autocomplete datum: $json');
        }

        this.id = json['id'];
        this.label = json['label'];

        if (json['extra'] != null) {
            this.extra = json['extra'];
        }
    }
}

/// A list of autocomplete items.
class AutocompleteData {
    List<AutocompleteDatum> list;

    bool get nothingFound => list.length == 0;

    AutocompleteData() {
        this.list = new List<AutocompleteDatum>();
    }

    AutocompleteData.fromJson(List<Map> json) {
        this.list = new List.generate(
            json.length,
            (index) => new AutocompleteDatum.fromJson(json[index])
        );
    }
}
