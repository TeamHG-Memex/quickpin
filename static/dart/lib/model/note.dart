/// A profile can have multiple usernames. This class encapsulates attributes of
/// a profile note.
class Note {
    int id;
    String body;
    String category;
    DateTime createdAt;
    int profileId;

    Note(this.body, this.category);

    Note.fromJson(Map json) {
        this.body = json['body'];
        this.category = json['category'];
        this.createdAt = DateTime.parse(json['created_at']);
        this.id = json['id'];
        this.profileId = json['profile_id'];
    }
}
