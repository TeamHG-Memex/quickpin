from flask import g, jsonify, request
from flask.ext.classy import FlaskView
from werkzeug.exceptions import BadRequest, NotFound

import app.config
from app.authorization import admin_required
from app.rest import url_for
from model import Credential


class CredentialView(FlaskView):
    '''
    Manipulate credentials.

    Requires an administrator account.
    '''

    decorators = [admin_required]

    def delete(self, site):
        '''
        Delete a credential pair for ``site``.

        **Example Response**

        .. sourcecode:: json

            {
                "message": "Credential deleted."
            }


        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token

        :>json str message: human-readable message

        :status 200: ok
        :status 401: authentication required
        :status 403: must be an administrator
        '''

        g.db.query(Credential).filter(Credential.site==site).delete()
        g.db.commit()

        return jsonify(message='Credential deleted.')

    def get(self, site):
        '''
        Get credential pair for ``site``.

        **Example Response**

        .. sourcecode:: json

            {
                "public": "scraper-guy",
                "secret": "my-password"
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token

        :>header Content-Type: application/json
        :>json str public: the public part of the credential pair, e.g. username
            or API ID
        :>json str secret: the secret part of the credential pair, e.g. password
            or API secret key

        :status 200: ok
        :status 401: authentication required
        :status 403: must be an administrator
        :status 404: no credentials exist for the requested site
        '''

        credential = g.db.query(Credential) \
                         .filter(Credential.site==site) \
                         .first()

        if site is None:
            message = 'No credential exists for the site "{}".'.format(site)
            raise NotFound(message)

        return jsonify(public=credential.public, secret=credential.secret)

    def index(self):
        '''
        Get a list of public credentials.

        Private credentials are not included in the response. You must use the
        `GET /api/credential/foo` endpoint to get the private part of the
        credential pair.

        **Example Response**

        .. sourcecode:: json

            {
                "credentials": {
                    "instagram": "my-instagram-user",
                    "twitter": "my-twitter-user",
                    ...
                }
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token

        :>header Content-Type: application/json
        :>json dict credentials: a dictionary where each key is a site name and
            each value is the public credential for that site.

        :status 200: ok
        :status 401: authentication required
        :status 403: must be an administrator
        :status 404: no credentials exist for the requested site
        '''

        credentials = {c.site:c.public for c in g.db.query(Credential).all()}

        return jsonify(credentials=credentials)

    def put(self, site):
        '''
        Create (or update) a credential pair ``site``.

        **Example Request**

        .. sourcecode:: json

            {
                "public": "scraper-guy",
                "secret": "my-password"
            }

        **Example Response**

        .. sourcecode:: json

            {
                "message": "Credential saved."
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :<json str public: the public part of the credential pair, e.g. username
            or API ID
        :<json str secret: the secret part of the credential pair, e.g. password
            or API secret key

        :>json str message: human-readable message

        :status 200: ok
        :status 401: authentication required
        :status 403: must be an administrator
        '''

        body = request.get_json()
        public = body.get('public', '').strip()
        secret = body.get('secret', '').strip()

        credential = g.db.query(Credential) \
                         .filter(Credential.site==site) \
                         .first()

        if credential is None:
            if public == '' or secret == '':
                raise BadRequest('Both "public" and "secret" is required ' \
                                 'when creating a credential.')

            credential = Credential(site, public, secret)
            g.db.add(credential)
        else:
            if public == '' and secret == '':
                raise BadRequest('Either "public" or "secret" is required ' \
                                 'when updating a credential.')

            if public != '':
                credential.public = public

            if secret != '':
                credential.secret = secret

        g.db.commit()

        return jsonify(message='Credential saved.')
