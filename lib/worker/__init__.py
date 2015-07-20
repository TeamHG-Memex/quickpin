'''
This package contains workers that handle work placed on the message queues.
'''

import rq
import scorched

import app.config
import app.database


_config = None
_db = None
_redis = None
_solr = None


def get_config():
    ''' Get application configuration. '''

    global _config

    if _config is None:
        _config = app.config.get_config()

    return _config


def get_db():
    ''' Get a database handle. '''

    global _db

    if _db is None:
        db_config = dict(get_config().items('database'))
        _db = app.database.get_engine(db_config)

    return _db


def get_job():
    ''' Return the RQ job instance. '''

    return rq.get_current_job(connection=get_redis())


def get_redis():
    ''' Get a Redis connection handle. '''

    global _redis

    if _redis is None:
        redis_config = dict(get_config().items('redis'))
        _redis = app.database.get_redis(redis_config)

    return _redis


def get_session():
    ''' Get a database session (a.k.a. transaction). '''

    return app.database.get_session(get_db())


def get_solr():
    ''' Get a Solr handle. '''

    global _solr

    if _solr is None:
        solr_config = dict(get_config().items('solr'))
        _solr = app.database.get_solr(solr_config)

    return _solr
