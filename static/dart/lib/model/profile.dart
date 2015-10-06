import 'package:quickpin/model/label.dart';

/// A model for a social media profile.
class Profile {
    static final ICON_CLASSES = {
        'instagram': 'fa-instagram',
        'twitter': 'fa-twitter',
    };

    String avatarUrl;
    String avatarThumbUrl;
    int id;
    bool isInteresting;
    bool isStub;
    String description;
    int followerCount;
    int friendCount;
    DateTime joinDate;
    DateTime lastUpdate;
    String location;
    String name;
    int postCount;
    bool private;
    String site, siteName;
    String timeZone;
    String upstreamId;
    String username;
    List<ProfileUsername> usernames;
    List<Label> labels;

    // Errors related to creating or loading this profile.
    String error;

    Profile(String username, String site) {
        this.username = username;
        this.site = site;
    }

    Profile.fromJson(Map json) {
        this.avatarUrl = json['avatar_url'];
        this.avatarThumbUrl = json['avatar_thumb_url'];
        this.description = json['description'];
        this.followerCount = json['follower_count'];
        this.friendCount = json['friend_count'];
        this.id = json['id'];
        this.isInteresting = json['is_interesting'];
        this.isStub = json['is_stub'];

        if (json['join_date'] != null) {
            this.joinDate = DateTime.parse(json['join_date']);
        }

        if (json['last_update'] != null) {
            this.lastUpdate = DateTime.parse(json['last_update']);
        }

        this.location = json['location'];
        this.name = json['name'];
        this.postCount = json['post_count'];
        this.private = json['private'];
        this.site = json['site'];
        this.siteName = json['site_name'];
        this.timeZone = json['time_zone'];
        this.upstreamId = json['original_id'];
        this.username = json['username'];

        if (json['usernames'] != null) {
            this.usernames = new List.generate(
                json['usernames'].length,
                (index) => new ProfileUsername.fromJson(json['usernames'][index])
            );
        }

        if (json['labels'] != null) {
            this.labels = new List.generate(
                json['labels'].length,
                (index) => new Label.fromJson(json['labels'][index])
            );
        }
    }

    /// Return the name of a Font Awesome icon class for this profile's site.
    String iconClass() {
        if (Profile.ICON_CLASSES[this.site] != null) {
            return Profile.ICON_CLASSES[this.site];
        } else {
            return 'fa-users';
        }
    }
}

/// A profile can have multiple usernames. This class encapsulates attributes of
/// a profile username.
class ProfileUsername {
    String username;
    DateTime startDate, endDate;

    ProfileUsername(this.username);

    ProfileUsername.fromJson(Map json) {
        this.username = json['username'];

        if (json['start_date'] != null) {
            this.startDate = DateTime.parse(json['start_date']);
        }

        if (json['end_date'] != null) {
            this.endDate = DateTime.parse(json['end_date']);
        }
    }
}
