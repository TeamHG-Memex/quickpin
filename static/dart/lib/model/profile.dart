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
    String name;
    List<ProfileName> names;

    // Errors related to creating or loading this profile.
    String error;

    Profile(String name, String site) {
        this.avatarUrls = new List<String>();
        this.name = name;
        this.site = site;
    }

    Profile.fromJson(Map json) {
        this.avatarUrls = json['avatar_urls'];
        this.description = json['description'];
        this.friendCount = json['friend_count'];
        this.followerCount = json['follower_count'];
        this.id = json['id'];
        this.lastUpdate = json['last_update'];
        this.name = json['name'];

        if (json['names'] != null) {
            this.names = new List.generate(
                json['names'].length,
                (index) => new ProfileName.fromJson(json['names'][index])
            );
        }

        this.originalId = json['original_id'];
        this.postCount = json['post_count'];

        if (json['join_date'] != null) {
            this.joinDate = DateTime.parse(json['join_date']);
        }

        this.joinDateIsExact = json['join_date_is_exact'];
        this.site = json['site'];
        this.siteName = json['site_name'];

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
