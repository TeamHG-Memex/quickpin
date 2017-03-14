import 'dart:html';

import 'package:angular/angular.dart';
import 'package:bootjack/bootjack.dart';

/// A component that presents a modal alert.
@Component(
    selector: 'modal-alert',
    templateUrl: 'packages/quickpin/component/modal/alert.html',
    useShadowDom: false
)
class ModalAlertComponent {
    String body;
    String icon;
    Modal modal;
    String title;
    String type;

    final Element _element;

    /// Constructor.
    ModalAlertComponent(this._element) {
        document.addEventListener('modal-alert', this.displayModal);

        document.body.onKeyUp.listen((e) {
            if (this.modal?.isShown && e.keyCode == KeyCode.ESC) {
                this.modal.hide();
            }
        });
    }

    /// This event handler displays the modal.
    void displayModal(Event e) {
        if (this.modal == null) {
            this.modal = Modal.wire(this._element.querySelector('div.modal'));
        }

        if (e.detail['body'] == null) {
            throw Exception('Modal event requires a body.');
        } else {
            this.body = e.detail['body'];
        }

        if (e.detail['title'] == null) {
            throw Exception('Modal event requires a title.');
        } else {
            this.title = e.detail['title'];
        }

        this.icon = e.detail['icon'] ?? 'fa-exclamation-triangle';
        this.type = e.detail['type'] ?? 'default';
        this.modal.show();
    }
}
