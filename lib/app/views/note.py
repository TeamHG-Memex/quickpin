import json
from flask.ext.classy import FlaskView
from flask import g, jsonify, request
from sqlalchemy.exc import DBAPIError
from werkzeug.exceptions import BadRequest, NotFound

from model.profile import Profile, ProfileNote
from app.authorization import login_required
from app.rest import get_int_arg, get_paging_arguments
from app.rest import url_for
import worker


class ProfileNoteView(FlaskView):
    ''' Notes for profiles. '''

    decorators = [login_required]

    def get(self, id_):
        '''
        Get the note identified by `id`.

        **Example Response**

        .. sourcecode: json

            {
                "id": 1,
                "category": "user annotation",
                "body": "This is a user annotation.",
                "profile_id": "10",
                "created_at": "2015-12-14T16:23:18.101558",
                "url": "https://quickpin/api/note/2",
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token

        :>header Content-Type: application/json
        :>json int id: unique identifier for note
        :>json str category: the user-defined category of this note
        :>json str body: the note
        :>json str profile_id: the unique id of the profile this note belongs to
        :>json str created_at: when the note was created as iso-formatted date string
        :>json str url: API endpoint URL for this note object

        :status 200: ok
        :status 400: invalid argument[s]
        :status 401: authentication required
        :status 404: note does not exist
        '''

        # Get note.
        id_ = get_int_arg('id_', id_)
        note = g.db.query(ProfileNote).filter(ProfileNote.id == id_).first()

        if note is None:
            raise NotFound("Note '%s' does not exist." % id_)

        response = note.as_dict()
        response['url'] = url_for('ProfileNoteView:get', id_=note.id)

        # Send response.
        return jsonify(**response)

    def post(self):
        '''
            Create profile notes.

            **Example Request**

            ..sourcode:: json

                {
                    "notes": [
                        {
                            "category": "user annotation",
                            "body": "this profile belongs to an interesting network",
                            "profile_id": "25 ",
                        },
                        {
                            "category": "user annotation",
                            "body": "this user does not exist anymore.",
                            "profile_id": "10",
                        },
                        ...
                    ]
                }

        **Example Response**

        ..sourcecode:: json

            {
                "message": "2 profile notes created."
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :>json list notes: a list of notes to create
        :>json str notes[n].category: the user-defined category of this note
        :>json str notes[n].body: the note
        :>json str notes[n]profile_id: the unique id of the profile this note belongs to

        :>header Content-Type: application/json
        :>json str message: api response message

        :status 202: created
        :status 400: invalid request body
        :status 401: authentication required
        '''

        request_json = request.get_json()
        redis = worker.get_redis()
        notes = list()
        profiles = list()

        required_fields = [
            'category',
            'body',
            'profile_id'
        ]

        # Validate input
        if 'notes' not in request_json:
            raise BadRequest('`notes` is required.')

        for note_json in request_json['notes']:
            request_fields = note_json.keys()
            # Check necessary fields are present
            missing_fields = set(required_fields) - set(request_fields)
            if len(missing_fields) > 0:
                raise BadRequest('All notes require: {}.'
                                 .format(','.join(required_fields)))
            # Check fields aren't empty
            for field in request_fields:
                if field.strip() == '':
                    raise BadRequest('{} is required and must not be empty.'.format(field))

            # Check the profile exists
            profile = g.db.query(Profile).filter(Profile.id == note_json['profile_id']).first()
            if profile is None:
                raise BadRequest('Profile `{}` does not exist.'.format(note_json['profile_id']))
            profiles.append(profile)

        # Create notes
        for note_json in request_json['notes']:
            try:
                note = ProfileNote(
                    category=note_json['category'].lower().strip(),
                    body=note_json['body'].strip(),
                    profile_id=note_json['profile_id'],
                )
                g.db.add(note)
                g.db.flush()
                notes.append(note)
            except:
                g.db.rollback()
                raise BadRequest('Notes could not be saved')

        # Save notes
        g.db.commit()

        # Publish SSEs
        for note in notes:
            redis.publish(
                'profile_notes',
                json.dumps(note.as_dict())
            )

        message = '{} new notes created'.format(len(notes))
        response = jsonify(
            message=message,
        )
        response.status_code = 202

        return response

    def put(self, id_):
        '''
        Update the note identified by `id`.

            **Example Request**

            ..sourcode:: json

                {
                    {
                        "category": "user annotation",
                        "body": "This profile belongs to two interesting networks",
                        "profile_id": "25 ",
                    },
                }

        **Example Response**

        ..sourcecode:: json
            {
                "id": "2",
                "category": "user annotation",
                "body": "This profile belongs to an interesting network",
                "profile_id": "25 ",
                "created_at": "2015-12-14T16:23:18.101558",
                "url": "https://quickpin/api/note/2",
            }


        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :>header Content-Type: application/json
        :>json int id: unique identifier for the note
        :>json str category: the user-defined category of this note
        :>json str body: the note
        :>json str profile_id: the unique id of the profile this note belongs to
        :>json str created_at: the iso-formatted creation time of the note
        :>json str url: API endpoint URL for this note object

        :status 202: created
        :status 400: invalid request body
        :status 401: authentication required
        '''

        # Get note.
        id_ = get_int_arg('id_', id_)
        note = g.db.query(ProfileNote).filter(ProfileNote.id == id_).first()

        if note is None:
            raise NotFound("Note '%s' does not exist." % id_)

        redis = worker.get_redis()
        request_json = request.get_json()

        # Validate data and set attributes
        if 'category' in request_json:
            if request_json['category'].strip() != '':
                note.category = request_json['category'].lower().strip()

        if 'body' in request_json:
            if request_json['body'].strip() != '':
                note.body = request_json['body'].strip()
            else:
                raise BadRequest('Attribute "name" cannot be an empty string')

        # Save the updated note
        try:
            g.db.commit()
        except DBAPIError:
            g.db.rollback()
            raise BadRequest('Could not update note.')

        # Generate SSE
        redis.publish(
            'profile_notes',
            json.dumps(note.as_dict())
        )
        response = note.as_dict()
        response['url'] = url_for('ProfileNoteView:get', id_=note.id)

        # Send response.
        return jsonify(**response)

    def delete(self, id_):
        '''
        Delete the note identified by `id`.

        **Example Response**

        ..sourcecode:: json

            {
                "message": "note `12` deleted",
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token

        :>header Content-Type: application/json
        :>json str message: the API response message
        :status 202: deleted
        :status 400: invalid request body
        :status 401: authentication required
        :status 404: note does not exist
        '''

        # Get note.

        redis = worker.get_redis()
        id_ = get_int_arg('id_', id_)
        note = g.db.query(ProfileNote).filter(ProfileNote.id == id_).first()

        if note is None:
            raise NotFound("Note `%s` does not exist." % id_)

        # Delete note
        g.db.delete(note)
        try:
            g.db.commit()
        except DBAPIError as e:
            raise BadRequest('Database error: {}'.format(e))

        message = 'Note `{}` deleted'.format(note.id)
        redis.publish(
            'profile_notes',
            json.dumps({
                'id': id_,
                'status': 'deleted',
            })
        )

        response = jsonify(message=message)
        response.status_code = 202

        return response

    def index(self):
        '''
        Return an array of all notes.

        **Example Response**

        .. sourcecode: json

            {
                "notes": [
                    {
                        "id": 1,
                        "category": "user annotation",
                        "body": "This is an interesting) profile.",

                        "profile_id": 1,
                        "created_at": "2015-12-15T10:41:55.792492",
                        "url": "https://quickpin/api/note/1",
                    },
                    ...
                ],
                "total_count": 1
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :query page: the page number to display (default: 1)
        :query rpp: the number of results per page (default: 10)
        :query profile_id: profile id to filter by


        :>header Content-Type: application/json
        :>json list notes: list of profile note objects
        :>json int list[n].id: unique identifier for the note
        :>json str list[n].category: the user-defined category of this note
        :>json str list[n].body: the note
        :>json str list[n].profile_id: the unique id of the profile this note belongs to
        :>json str list[n].created_at: the iso-formatted creation time of the note
        :>json str list[n].url: API endpoint URL for this note object

        :status 200: ok
        :status 400: invalid argument[s]
        :status 401: authentication required
        '''

        # Parse paging arguments
        page, results_per_page = get_paging_arguments(request.args)
        # Create base query
        query = g.db.query(ProfileNote)
        # Parse filter arguments
        profile_id = request.args.get('profile_id', None)
        if profile_id is not None:
            query = query.filter(ProfileNote.profile_id == profile_id)
        # Store the total result count before paging arguments limit result set
        total_count = query.count()
        # Apply paging arguments
        query = query.order_by(ProfileNote.category.asc()) \
                     .limit(results_per_page) \
                     .offset((page - 1) * results_per_page)
        # Add API endpoint URL for each note object
        notes = list()
        for note in query:
            data = note.as_dict()
            data['url'] = url_for('ProfileNoteView:get', id_=note.id)
            notes.append(data)

        return jsonify(
            notes=notes,
            total_count=total_count
        )
