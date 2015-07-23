import time

from flask import g, request, Response, send_from_directory
from flask.ext.classy import FlaskView
from werkzeug.exceptions import NotAcceptable, NotFound

from app.authorization import login_required
import app.config
import app.database
from app.rest import url_for
from model import File


class NotificationView(FlaskView):
    '''
    Send notifications using Server-Sent Events (SSE).

    Based on this:
    http://stackoverflow.com/questions/13386681/streaming-data-with-python-and-flask
    '''

    CHANNELS = (
        'avatar',
        'profile',
    )

    decorators = [login_required]

    def index(self):
        ''' Open an SSE stream. '''

        if request.headers.get('Accept') == 'text/event-stream':
            redis = app.database.get_redis(dict(g.config.items('redis')))
            pubsub = redis.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe(*self.__class__.CHANNELS)
            return Response(self._stream(pubsub), content_type='text/event-stream')
        else:
            message = 'This endpoint is only for use with server-sent ' \
                      'events (SSE).'
            raise NotAcceptable(message)

    def _stream(self, pubsub):
        ''' Stream events. '''

        for message in pubsub.listen():
            channel = message['channel'].decode('utf8')
            data = message['data'].decode('utf8')
            yield 'event: {}\ndata: {}\n\n'.format(channel, data)
