import 'dart:async';
import 'dart:html';

import 'package:angular/angular.dart';
import 'package:bootjack/bootjack.dart';

/// A component that presents a modal form.
@Component(
    selector: 'modal-form',
    templateUrl: 'packages/quickpin/component/modal/form.html',
    useShadowDom: false
)
class ModalFormComponent {
    @NgOneWay('on-submit')
    Function onSubmit;

    @NgOneWay('title')
    String title;

    @NgOneWay('modal-type')
    String modalType = 'default';

    @NgOneWay('submit-icon')
    String submitIcon = 'fa-floppy-o';

    @NgOneWay('submit-text')
    String submitText = 'Save';

    bool busy = false;
    String error;
    Modal modal;

    final Element _element;
    final String _inputQuery =
        'input[type=checkbox], input[type=radio]:checked, '
        'input[type=password], input[type=text], select, textarea';

    final String _customQuery = '[custom-form]';
    final RouteProvider _rp;

    /// Constructor.
    ModalFormComponent(this._element, this._rp) {
        this._element.addEventListener('show-modal-form', this.show);

        document.body.onKeyUp.listen((e) {
            if (this.modal?.isShown && e.keyCode == KeyCode.ESC && !this.busy) {
                this.modal.hide();
            }
        });

        // Hide modal when route changes.
        RouteHandle rh = this._rp.route.newHandle();

        rh.onLeave.take(1).listen((_) {
            if (this.modal != null && this.modal.isShown) {
                this.reset();
            }
        });
    }

    /// Clear error message and the "has-error" flag on any fields that have it.
    void clearErrors() {
        this.error = null;

        for (Element el in this._element.querySelectorAll('.has-error')) {
            el.classes.remove('has-error');
        }
    }

    /// Called when form completes successfully.
    ///
    /// This hides the modal and also resets any form inputs that do not have
    /// the `no-auto-reset` attribute.
    void reset() {
        this._resetFormData();
        this.modal.hide();
        this.busy = false;
    }

    /// This event handler displays the modal.
    void show(Event e) {
        if (this.modal == null) {
            this.modal = Modal.wire(this._element.querySelector('div.modal'));
        }

        this.modal.show();

        new Timer(new Duration(milliseconds:500), () {
            String base = 'label.control-label + div ';
            String query = '$base input, $base select, $base textarea';
            Element initialFocusEl = this._element.querySelector(query);

            if (initialFocusEl != null) {
                initialFocusEl.focus();
            }
        });
    }

    /// Call the registered submit handler.
    void submit() {
        this.busy = true;
        this.clearErrors();
        Completer<Map> formCompleter = new Completer<Map>();
        Map formData = this._getFormData();
        this.onSubmit(formData, formCompleter);

        // Handle form completion: hide if successful or show errors errors if
        // failed.
        formCompleter.future.then((errors) {
            this.busy = false;

            if (errors == null || errors.isEmpty) {
                this.reset();
            } else {
                this.error = errors.values.join(' ');

                for (String fieldName in errors.keys) {
                    if (fieldName != null) {
                        this._markError(fieldName);
                    }
                }
            }
        });
    }

    /// Iterate over all children of this element and return a map of all of
    /// the form elements and their values.
    ///
    /// This should support native HTML form elements as well as our custom
    /// elements.
    Map _getFormData() {
        Map formData = new Map();
        Function qsa = this._element.querySelectorAll;

        for (HtmlElement input in qsa(this._inputQuery)) {
            String name = input.attributes['name'];
            formData[name] = input.value.trim();
        }

        for (HtmlElement custom in qsa(this._customQuery)) {
            String name = custom.attributes['name'];
            formData[name] = custom.attributes['custom-form'].trim();
        }
        return formData;
    }

    /// Mark field[s] as having an error.
    void _markError(String fieldName) {
        String query = '[name=$fieldName]';
        ElementList fields = this._element.querySelectorAll(query);

        for (Element field in fields) {
            Element parent = field.parent;

            while (parent != null && !parent.classes.contains('form-group')) {
                parent = parent.parent;
            }

            if (parent != null) {
                parent.classes.add('has-error');
            }
        }
    }

    /// Iterate over all children of this element and resets form input values
    /// except for elements with the `preserve-after-submit` attribute.
    ///
    /// This should support native HTML form elements as well as our custom
    /// elements.
    Map _resetFormData() {
        Function qsa = this._element.querySelectorAll;

        for (HtmlElement input in qsa(this._inputQuery)) {
            if (!input.attributes.containsKey('no-auto-reset')) {
                if (input is InputElement || input is TextAreaElement) {
                    input.value = input.defaultValue;
                } else if (input is PasswordInputElement) {
                    input.value = '';
                } else if (input is SelectElement) {
                    input.selectedIndex = 0;
                } else {
                    String msg = 'Do not know how to reset element of type: '
                                 '${input.runtimeType}';
                    throw new Exception(msg);
                }
            }
        }

        for (HtmlElement custom in qsa(this._customQuery)) {
            if (!custom.attributes.containsKey('no-auto-reset')) {
                custom.dispatchEvent(new CustomEvent('reset'));
            }
        }
    }
}

/// Show a modal form with a given selector.
void showModalForm(String selector) {
    Element target = querySelector(selector);

    if (target == null) {
        throw new Exception('No modal form matches selector "$selector"');
    } else {
        target.dispatchEvent(new CustomEvent('show-modal-form'));
    }
}
