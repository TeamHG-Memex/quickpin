''' Message queues. '''

from rq import Queue

import app.config


_config = app.config.get_config()
_redis = app.database.get_redis(dict(_config.items('redis')))

index_queue = Queue('index', connection=_redis)
