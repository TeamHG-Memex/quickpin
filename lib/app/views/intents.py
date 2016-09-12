import os
import requests
from requests.auth import HTTPBasicAuth
from flask import g, jsonify
from flask_classy import FlaskView
from werkzeug.exceptions import NotFound

import app.config
from app.authorization import login_required
from model.configuration import get_config


class IntentsView(FlaskView):
    ''' Manipulate files. '''

    decorators = [login_required]

    def index(self):
        '''
        Get QCR intents data.

        **Example Response**

        .. sourcecode:: json

            {
                "Google Maps":{
                    "intents":{
                        "geoloc":"@{{geoloc.lat}},{{geoloc.long}},12z",
                        "geobounds":"@{{geobounds.lat0}},{{geobounds.long0}},12z"
                    },
                    "hide":true,
                    "name":"Google Maps",
                    "url":"https://www.google.com/maps",
                    "desc":"Interactive maps",
                    "thumbnail":"googlemaps.png",
                    "icon":"googlemaps.png"
                },
                ...
            }

        :status 200: ok
        :status 401: authentication required
        :status 404: intents not found
        '''

        url = get_config(g.db, 'intents_url', required=True)
        username = get_config(g.db, 'intents_username', required=True)
        print(username)
        password = get_config(g.db, 'intents_password', required=True)

        if url is None or url.value.strip() == '':
            raise NotFound('Intents url is not configured.')

        if username is None or password is None:
            raise NotFound('Intents credentials not configured.')

        if username.value.strip() == ''  or password.value.strip == '':
            raise NotFound('Intents credentials not configured.')

        try:
            response = requests.get(
                url.value,
                auth=HTTPBasicAuth(username.value, password.value),
                verify=False,
                timeout=5
            )
        except:
            raise NotFound('Intents data could not be retrieved from server.')

        return jsonify(response.json())
