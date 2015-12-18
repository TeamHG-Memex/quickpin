from flask.ext.classy import FlaskView
from flask import g, jsonify, request
import json
from sqlalchemy.exc import IntegrityError, DBAPIError
from werkzeug.exceptions import BadRequest, NotFound

import worker
from model.label import Label
from app.authorization import login_required
from app.rest import get_int_arg
from app.rest import get_paging_arguments
from app.rest import url_for


class LabelView(FlaskView):
    ''' Labels for profiles. '''

    decorators = [login_required]

    def get(self, id_):
        '''
        Get the label identified by `id`.

        **Example Response**

        .. sourcecode:: json

            {
                "id": 1,
                "name": "gender",
                "url": "https://quickpin/api/label/1",
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token

        :>header Content-Type: application/json
        :>json int id: unique identifier for label
        :>json str name: the label name
        :>json str url: URL endpoint for retriving more data about this label

        :status 200: ok
        :status 400: invalid argument[s]
        :status 401: authentication required
        :status 404: label does not exist
        '''

        # Get label.
        id_ = get_int_arg('id_', id_)
        label = g.db.query(Label).filter(Label.id == id_).first()

        if label is None:
            raise NotFound("Label '%s' does not exist." % id_)

        response = label.as_dict()
        response['url'] = url_for('LabelView:get', id_=label.id)

        # Send response.
        return jsonify(**response)

    def post(self):
        '''
        Create a label.

        **Example Request**

        .. sourcecode:: json

            {
                "labels": [
                    {"name": "gender"},
                    {"name": "age"},
                    ...
                ]
            }

        **Example Response**

        .. sourcecode:: json

            {
                "message": "2 new labels created."
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :>json list labels: a list of labels to create
        :>json str labels[n].name: name of label to create

        :>header Content-Type: application/json
        :>json str message: api response message

        :status 202: created
        :status 400: invalid request body
        :status 401: authentication required
        '''

        request_json = request.get_json()
        redis = worker.get_redis()
        labels = list()

        # Validate input and create labels
        for t in request_json['labels']:
            if t['name'].strip() == '':
                raise BadRequest('Label name is required')
            else:
                try:
                    label = Label(name=t['name'].lower().strip())
                    g.db.add(label)
                    g.db.flush()
                    redis.publish('label', json.dumps(label.as_dict()))
                    labels.append(label.as_dict())
                except IntegrityError:
                    g.db.rollback()
                    raise BadRequest(
                        'Label "{}" already exists'.format(label.name)
                    )
                except AssertionError:
                    g.db.rollback()
                    raise BadRequest(
                        '"{}" contains non-alphanumeric character'
                        .format(t['name'])
                    )

        # Save labels
        g.db.commit()

        message = '{} new labels created'.format(len(request_json['labels']))
        labels = labels
        response = jsonify(
            message=message,
            labels=labels
        )
        response.status_code = 202

        return response

    def index(self):
        '''
        Return an array of all labels.

        **Example Response**

        .. sourcecode:: json

            {
                "labels": [
                    {
                        "id": 1,
                        "name": "gender",
                        "url": "https://quickpin/api/label/1",
                    },
                    ...
                ],
                "total_count": 2
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :query page: the page number to display (default: 1)
        :query rpp: the number of results per page (default: 10)


        :>header Content-Type: application/json
        :>json list labels: a list of label objects
        :>json int labels[n].id: unique identifier for profile
        :>json str labels[n].name: the label name
        :>json str labels[n].url: URL endpoint for retriving more data
            about this label

        :status 200: ok
        :status 400: invalid argument[s]
        :status 401: authentication required
        '''

        page, results_per_page = get_paging_arguments(request.args)
        query = g.db.query(Label)
        total_count = query.count()
        query = query.order_by(Label.name.asc()) \
                     .limit(results_per_page) \
                     .offset((page - 1) * results_per_page)

        labels = list()

        for label in query:
            data = label.as_dict()
            data['url'] = url_for('LabelView:get', id_=label.id)
            labels.append(data)

        return jsonify(
            labels=labels,
            total_count=total_count
        )

    def put(self, id_):
        '''
        Update the label identified by `id`.

        **Example Request**

        .. sourcecode:: json

            {
                {"name": "gender"},
            }

        **Example Response**

        .. sourcecode:: json

            {
                "id": "2",
                "name": "gender",
                "url": "https://quickpin/api/label/1",
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :>json str name: the value of the name attribute

        :>header Content-Type: application/json
        :>json int id: unique identifier for label
        :>json str name: the label name
        :>json str url: URL endpoint for retriving more data about this label

        :status 202: created
        :status 400: invalid request body
        :status 401: authentication required
        '''

        # Get label.
        id_ = get_int_arg('id_', id_)
        label = g.db.query(Label).filter(Label.id == id_).first()

        if label is None:
            raise NotFound("Label '%s' does not exist." % id_)

        request_json = request.get_json()

        # Validate data and set attributes
        if 'name' in request_json:
            if request_json['name'].strip() != '':
                label.name = request_json['name'].lower().strip()
            else:
                raise BadRequest('Attribute "name" cannot be an empty string')
        else:
            raise BadRequest('Attribue "name" is required')

        # Save the updated label
        try:
            g.db.commit()
        except DBAPIError as e:
            g.db.rollback()
            raise BadRequest('Database error: {}'.format(e))

        response = label.as_dict()
        response['url'] = url_for('LabelView:get', id_=label.id)

        # Send response.
        return jsonify(**response)

    def delete(self, id_):
        '''
        Delete the label identified by `id`.

        **Example Response**

        .. sourcecode:: json

            {
                "message": "Label `gender` deleted",
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token

        :>header Content-Type: application/json
        :>json str message: the API response message

        :status 202: deleted
        :status 400: invalid request body
        :status 401: authentication required
        :status 404: label does not exist
        '''

        # Get label.
        id_ = get_int_arg('id_', id_)
        label = g.db.query(Label).filter(Label.id == id_).first()

        if label is None:
            raise NotFound("Label '%s' does not exist." % id_)

        # Delete label
        g.db.delete(label)
        try:
            g.db.commit()
        except DBAPIError as e:
            raise BadRequest('Database error: {}'.format(e))

        message = 'Label {} deleted'.format(label.name)
        response = jsonify(message=message)
        response.status_code = 202

        return response
