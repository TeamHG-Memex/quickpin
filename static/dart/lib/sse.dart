import 'dart:html';

import 'package:angular/angular.dart';
import 'package:quickpin/authentication.dart';

/// Handles server-sent events.
@Injectable()
class SseController {
    AuthenticationController _auth;
    EventSource _eventSource;

    /// Constructor
    SseController(this._auth) {
        String url = '/api/notification/?xauth=' + Uri.encodeFull(this._auth.token);
        this._eventSource = new EventSource(url);
        this._eventSource.onError.listen((Event e) {
            window.console.log('Error connecting to SSE!');
        });
    }

    /// Wrapper around the event source's addEventListener.
    void addEventListener(String type, EventListener listener, [bool useCapture]) {
        this._eventSource.addEventListener(type, listener, useCapture);
    }

    /// Wrapper around the event source's removeEventListener.
    void removeEventListener(String type, EventListener listener, [bool useCapture]) {
        this._eventSource.removeEventListener(type, listener, useCapture);
    }
}
