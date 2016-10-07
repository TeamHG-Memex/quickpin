/*
 * Instead of using an expensive subquery to find a profile's current avatar,
 * denormalize the model by placing a `current_avatar_id` column into the
 * profile table.
 */

ALTER TABLE profile ADD current_avatar_id INTEGER;
ALTER TABLE ONLY profile
    ADD CONSTRAINT fk_profile_current_avatar
    FOREIGN KEY (current_avatar_id) REFERENCES avatar(id);
