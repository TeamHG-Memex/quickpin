/// A model for a social media profile.
class Profile {
    static final ICON_CLASSES = {
        'instagram': 'fa-instagram',
        'twitter': 'fa-twitter',
    };

    List<String> avatarUrls;
    int id;
    String site, siteName;
    String originalId;
    String description;
    int friendCount, followerCount, postCount;
    DateTime joinDate;
    bool joinDateIsExact;
    DateTime lastUpdate;
    List<ProfileName> names;

    Profile(String name, String site) {
        this.avatarUrls = new List<String>();
        this.names = new List<ProfileName>();
        this.names.add(new ProfileName(name));
        this.site = site;
    }

    Profile.fromJson(Map json) {
        this.avatarUrls = json['avatar_urls'];
        this.id = json['id'];
        this.site = json['site'];
        this.siteName = json['site_name'];
        this.originalId = json['original_id'];
        this.description = json['description'];
        this.friendCount = json['friend_count'];
        this.followerCount = json['follower_count'];
        this.postCount = json['post_count'];

        if (json['join_date'] != null) {
            this.joinDate = DateTime.parse(json['join_date']);
        }

        this.joinDateIsExact = json['join_date_is_exact'];
        this.lastUpdate = json['last_update'];

        this.names = new List.generate(
            json['names'].length,
            (index) => new ProfileName.fromJson(json['names'][index])
        );
    }

    /// Return a URL for this profile's avatar image.
    String avatarUrl() {
        if (this.avatarUrls.length > 0) {
            return this.avatarUrls[0];
        } else {
            return '/static/img/default_user_thumb_large.png';
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

/// A profile can have multiple names. This class encapsulates attributes of
/// a profile name.
class ProfileName {
    String name;
    DateTime startDate, endDate;

    ProfileName(this.name);

    ProfileName.fromJson(Map json) {
        this.name = json['name'];

        if (json['start_date'] != null) {
            this.startDate = DateTime.parse(json['start_date']);
        }

        if (json['end_date'] != null) {
            this.endDate = DateTime.parse(json['end_date']);
        }
    }
}
