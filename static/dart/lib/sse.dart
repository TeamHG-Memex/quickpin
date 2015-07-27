import 'dart:html';

import 'package:angular/angular.dart';
import 'package:quickpin/authentication.dart';

/// Handles server-sent events.
@Injectable()
class SseController {
    Stream<Event> onAvatar;
    Stream<Event> onProfile;

    AuthenticationController _auth;
    EventSource _eventSource;
    RouteProvider _rp;

    /// Constructor
    SseController(this._auth, this._rp) {
        String url = '/api/notification/?xauth=' + Uri.encodeFull(this._auth.token);
        this._eventSource = new EventSource(url);

        this._eventSource.onError.listen((Event e) {
            window.console.log('Error connecting to SSE!');
        });

        // Set up event streams.
        this.onAvatar = this._eventSource.on['avatar'];
        this.onProfile = this._eventSource.on['profile'];
    }
}
