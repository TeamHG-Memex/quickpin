/*
* Add profile_note table.
*/

CREATE SEQUENCE profile_note_id_seq
    START WITH 1                                                    
    INCREMENT BY 1                                                                  
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;                                                         


CREATE TABLE profile_note (
    id integer DEFAULT nextval('profile_note_id_seq') PRIMARY KEY,
    category character varying(255),
    body text,                    
    created_at timestamp without time zone NOT NULL,
    profile_id integer NOT NULL
);

ALTER SEQUENCE profile_note_id_seq OWNED BY profile_note.id;

ALTER TABLE ONLY profile_note 
    ADD CONSTRAINT fk_profile_note_profile
    FOREIGN KEY (profile_id) REFERENCES profile(id);

