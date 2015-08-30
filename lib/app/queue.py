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
_index_queue = Queue('index', connection=_redis)
_scrape_queue = Queue('scrape', connection=_redis)


def schedule_avatar(profile, avatar_url):
    ''' Queue a job to fetch an avatar image for the specified profile. '''

    job = _scrape_queue.enqueue(
        worker.scrape.scrape_twitter_avatar,
        profile.id,
        avatar_url
    )

    description = 'Getting avatar image for "{}" on "{}"' \
                  .format(profile.username, profile.site_name())

    worker.init_job(job, description)


def schedule_index(profile):
    ''' Queue a job to index the specified profile. '''

    job = _index_queue.enqueue(worker.index.index_profile, profile.id)

    description = 'Indexing profile "{}" on "{}"' \
                  .format(profile.username, profile.site_name())

    worker.init_job(job, description)


def schedule_posts(profile):
    ''' Queue a job to get posts for the specified profile. '''

    job = _scrape_queue.enqueue(worker.scrape.scrape_twitter_posts, profile.id)

    description = 'Getting posts for "{}" on "{}"' \
                  .format(profile.username, profile.site_name())

    worker.init_job(job, description)


def schedule_profile(site, username):
    ''' Queue a job to fetch the specified profile from a social media site. '''

    job = _scrape_queue.enqueue(
        worker.scrape.scrape_profile,
        site,
        username,
        timeout=60
    )

    description = 'Scraping bio for "{}" on "{}"'.format(username, site)
    worker.init_job(job, description)


def schedule_relations(profile):
    ''' Queue a job to get relations for the specified profile. '''

    description = 'Getting friends & followers for "{}" on "{}"' \
                  .format(profile.username, profile.site_name())

    job = _scrape_queue.enqueue(
        worker.scrape.scrape_twitter_relations,
        profile.id,
        timeout=3600
    )

    worker.init_job(job, description)


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
