import 'package:quickpin/model/coordinate.dart';

/// A model for a social media post.
class Post {
    String content;
    int id;
    String language;
    DateTime lastUpdate;
    Coordinate location;
    DateTime upstreamCreated;
    String upstreamId;

    Post.fromJson(Map json) {
        this.content = json['content'];
        this.id = json['id'];
        this.language = json['language'];

        if (json['last_update'] != null) {
            this.lastUpdate = DateTime.parse(json['last_update']);
        }

        this.location = new Coordinate(json['location'][0], json['location'][1]);

        if (json['upstream_created'] != null) {
            this.upstreamCreated = DateTime.parse(json['upstream_created']);
        }

        this.upstreamId = json['upstream_id'];
    }
}
