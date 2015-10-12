/// A model for a profile label.
class Label {

    String name;
    int id;

    // Errors related to creating or loading this profile.
    String error;

    Label(String name) {
        this.name = name;
    }

    Label.fromJson(Map json) {
        this.name = json['name'];
        this.id = json['id'];
    }

}
