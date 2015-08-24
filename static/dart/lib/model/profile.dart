/// A model for a social media profile.
class Profile {
    static final ICON_CLASSES = {
        'instagram': 'fa-instagram',
        'twitter': 'fa-twitter',
    };

    String avatarUrl;
    List<String> avatarUrls;
    String avatarThumbUrl;
    int id;
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

    // Errors related to creating or loading this profile.
    String error;

    Profile(String username, String site) {
        this.avatarUrls = new List<String>();
        this.username = username;
        this.site = site;
    }

    Profile.fromJson(Map json) {
        if (json['avatar_urls'] != null && json['avatar_urls'].length > 0) {
            this.avatarUrl = json['avatar_urls'][0];
        } else {
            this.avatarUrl = '/static/img/default_user_thumb_large.png';
        }

        this.avatarUrls = json['avatar_urls'];

        if (json['avatar_thumb_url'] != null) {
            this.avatarThumbUrl = json['avatar_thumb_url'];
        } else {
            this.avatarThumbUrl = '/static/img/default_user_thumb.png';
        }

        this.description = json['description'];
        this.followerCount = json['follower_count'];
        this.friendCount = json['friend_count'];
        this.id = json['id'];
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
