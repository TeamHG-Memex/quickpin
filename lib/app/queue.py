''' Message queues. '''

import json

from rq import Queue

import app.config
import worker
import worker.index
import worker.scrape
import worker.sleep


_config = app.config.get_config()
_redis = app.database.get_redis(dict(_config.items('redis')))
_redis_worker = dict(_config.items('redis_worker'))
_index_queue = Queue('index', connection=_redis)
_scrape_queue = Queue('scrape', connection=_redis)


def schedule_avatar(profile, avatar_url):
    ''' Queue a job to fetch an avatar image for the specified profile. '''

    job = _scrape_queue.enqueue_call(
        func=worker.scrape.scrape_avatar,
        args=(profile.id, profile.site, avatar_url),
        timeout=_redis_worker['avatar_timeout']
    )

    description = 'Getting avatar image for "{}" on {}' \
                  .format(profile.username, profile.site_name())

    worker.init_job(job=job, description=description, profile_id=profile.id)


def schedule_index_profile(profile):
    ''' Queue a job to index the specified profile. '''

    job = _index_queue.enqueue_call(
        func=worker.index.index_profile,
        args=[profile.id],
        timeout=_redis_worker['solr_timeout']
    )

    description = 'Indexing profile "{}" on {}' \
                  .format(profile.username, profile.site_name())

    worker.init_job(job=job, description=description)


def schedule_index_posts(post_ids):
    ''' Queue a job to index the specified posts. '''

    job = _index_queue.enqueue_call(
        func=worker.index.index_posts,
        kwargs={'post_ids':post_ids},
        timeout=_redis_worker['solr_timeout']
    )

    description = 'Indexing {} posts' \
                  .format(len(post_ids))

    worker.init_job(job=job, description=description)


def schedule_profile(site, username):
    ''' Queue a job to fetch the specified profile from a social media site. '''

    job = _scrape_queue.enqueue_call(
        func=worker.scrape.scrape_profile,
        args=(site,username),
        timeout=_redis_worker['profile_timeout']
    )

    description = 'Scraping bio for "{}" on {}'.format(username, site)
    worker.init_job(job=job, description=description)

def schedule_profile_id(site, upstream_id, profile_id):
    ''' Queue a job to fetch the specified profile from a social media site. '''

    job = _scrape_queue.enqueue_call(
        func=worker.scrape.scrape_profile_by_id,
        args=(site,upstream_id),
        timeout=_redis_worker['profile_timeout']
    )

    description = 'Scraping bio for "{}" on {}'.format(upstream_id, site)
    worker.init_job(job=job, description=description, profile_id=profile_id)

def schedule_posts(profile, recent=True):
    ''' Queue a job to get posts for the specified profile. '''

    scrapers = {
        'instagram': worker.scrape.scrape_instagram_posts,
        'twitter': worker.scrape.scrape_twitter_posts,
    }

    description = 'Getting posts for "{}" on {}' \
                  .format(profile.username, profile.site_name())
    type_ ='posts'

    #job = _scrape_queue.enqueue(scrapers[profile.site], profile.id, recent)
    job = _scrape_queue.enqueue_call(
        func=scrapers[profile.site],
        args=(profile.id, recent),
        timeout=_redis_worker['posts_timeout']
    )
    worker.init_job(
        job=job,
        description=description,
        profile_id=profile.id,
        type_=type_
    )


def schedule_relations(profile):
    ''' Queue a job to get relations for the specified profile. '''

    scrapers = {
        'instagram': worker.scrape.scrape_instagram_relations,
        'twitter': worker.scrape.scrape_twitter_relations,
    }

    description = 'Getting friends & followers for "{}" on {}' \
                  .format(profile.username, profile.site_name())
    type_ = 'relations'

    job = _scrape_queue.enqueue_call(
        func=scrapers[profile.site],
        args=[profile.id],
        timeout=_redis_worker['relations_timeout']
    )
    worker.init_job(
        job=job,
        description=description,
        profile_id=profile.id,
        type_=type_
    )


def schedule_sleep_determinate(period):
    ''' Schedule a determinate sleep task (useful for testing). '''

    description = 'Determinate sleep for {} seconds'.format(period)

    job = _scrape_queue.enqueue(
        worker.sleep.sleep_determinate,
        period,
        timeout=period + 1
    )

    worker.init_job(job, description)


def schedule_sleep_exception(period):
    ''' Schedule a sleep task that raises an exception (useful for testing). '''

    description = 'Exception sleep for {} seconds'.format(period)

    job = _scrape_queue.enqueue(
        worker.sleep.sleep_exception,
        period,
        timeout=period + 1
    )

    worker.init_job(job, description)


def schedule_sleep_indeterminate(period):
    ''' Schedule an indeterminate sleep task (useful for testing). '''

    description = 'Indeterminate sleep for {} seconds'.format(period)

    job = _scrape_queue.enqueue(
        worker.sleep.sleep_indeterminate,
        period,
        timeout=period + 1
    )

    worker.init_job(job, description)
