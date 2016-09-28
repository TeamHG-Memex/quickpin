""" Message queues. """

import json

from rq import Connection, Queue

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


def dummy_job():
    """
    This dummy job is used by init_queues().

    It must be defined at the module level so that Python RQ can import it;
    it cannot be an anonymous or nested function.
    """
    pass


def init_queues(redis):
    """
    Python RQ creates queues lazily, but we want them created eagerly.

    This function submits a dummy job to each queue to force Python RQ to
    create that queue.
    """

    queues = {q for q in globals().values() if type(q) is Queue}

    with Connection(redis):
        for queue in queues:
            queue.enqueue(dummy_job)


def remove_unused_queues(redis):
    """
    Remove queues in RQ that are not defined in this file.

    This is useful for removing queues that used to be defined but were later
    removed.
    """

    queue_names = {q.name for q in globals().values() if type(q) is Queue}

    with Connection(redis):
        for queue in Queue.all():
            if queue.name not in queue_names:
                queue.empty()
                redis.srem('rq:queues', 'rq:queue:{}'.format(queue.name))


def schedule_avatar(profile, avatar_url):
    """ Queue a job to fetch an avatar image for the specified profile. """

    job = _scrape_queue.enqueue_call(
        func=worker.scrape.scrape_avatar,
        args=(profile.id, profile.site, avatar_url),
        timeout=_redis_worker['avatar_timeout']
    )

    description = 'Getting avatar image for "{}" on {}' \
                  .format(profile.username, profile.site_name())

    worker.init_job(job=job, description=description, profile_id=profile.id)


def schedule_index_profile(profile):
    """ Queue a job to index the specified profile. """

    job = _index_queue.enqueue_call(
        func=worker.index.index_profile,
        args=[profile.id],
        timeout=_redis_worker['solr_timeout']
    )

    description = 'Indexing profile "{}" on {}' \
                  .format(profile.username, profile.site_name())

    worker.init_job(job=job, description=description)


def schedule_index_posts(post_ids):
    """ Queue a job to index the specified posts. """

    job = _index_queue.enqueue_call(
        func=worker.index.index_posts,
        kwargs={'post_ids': post_ids},
        timeout=_redis_worker['solr_timeout']
    )

    description = 'Indexing {} posts' \
                  .format(len(post_ids))

    worker.init_job(job=job, description=description)


def schedule_delete_profile_from_index(profile):
    """ 
    Queue a job to delete the specified profile from the index.
    """

    job = _index_queue.enqueue_call(
        func=worker.index.delete_profile,
        args=[profile.id],
        timeout=_redis_worker['solr_timeout']
    )

    description = 'Deleting profile "{}" on {} from index' \
                  .format(profile.username, profile.site_name())

    worker.init_job(job=job, description=description)


def schedule_delete_profile_posts_from_index(profile_id):
    """ 
    Queue a job to delete the specified profile posts from the index.
    """

    job = _index_queue.enqueue_call(
        func=worker.index.delete_profile_posts,
        args=[profile_id],
        timeout=_redis_worker['solr_timeout']
    )

    description = 'Deleting profile "{}" posts from index' \
                  .format(profile_id)

    worker.init_job(job=job, description=description)


def schedule_delete_profile_from_index(profile_id):
    """ Queue a job to index the specified profile. """

    job = _index_queue.enqueue_call(
        func=worker.index.delete_profile,
        args=[profile_id],
        timeout=_redis_worker['solr_timeout']
    )

    description = 'Deleting profile "{}" from index' \
                  .format(profile_id)

    worker.init_job(job=job, description=description)


def schedule_profile(site, username, stub=False):
    """ Queue a job to fetch the specified profile from a social media site. """

    job = _scrape_queue.enqueue_call(
        func=worker.scrape.scrape_profile,
        args=(site, [username], stub),
        timeout=_redis_worker['profile_timeout']
    )

    description = 'Scraping bio for "{}" on {}'.format(username, site)
    worker.init_job(job=job, description=description)


def schedule_profile_id(site, upstream_id, profile_id=None, stub=False):
    """ Queue a job to fetch the specified profile from a social media site. """

    job = _scrape_queue.enqueue_call(
        func=worker.scrape.scrape_profile_by_id,
        args=(site, [upstream_id], stub),
        timeout=_redis_worker['profile_timeout']
    )

    description = 'Scraping bio for "{}" on {}'.format(upstream_id, site)
    worker.init_job(job=job, description=description, profile_id=profile_id)


def schedule_profiles(profiles, stub=False):
    """
    Queue jobs to fetch a list of profiles from a social media site.

    Profile scraping jobs are chunked according to maximum API request size

    Twitter:
        Supports 100 users per lookup:
        https://dev.twitter.com/rest/reference/get/users/lookup

    Instagram:
        Supports 1 user per lookup:
        https://instagram.com/developer/endpoints/users/#get_users_search

    Parameters:

        'profiles' (list) - A list of profile dictionaries

            Each dictionary specifiies profile username or id and social media
            site name ("twitter", "instagram").

            Example:

                profiles = [
                    {
                        'username': 'hyperiongray',
                        'site': 'twitter',
                    },
                    {
                        'upstream_id': '343432',
                        'site': 'instagram',
                    },
                    ...
                ]

        'stub' (bool) - whether or not to import the profile as a stub
    """

    # Aggregate profiles by site and API request type (username or ID)
    site_profiles = {}
    for profile in profiles:
        if profile['site'] not in site_profiles:
            site_profiles[profile['site']] = {
                'username': [],
                'upstream_id': []
            }
        if 'upstream_id' in profile:
            site_profiles[profile['site']]['upstream_id'].append(profile)
        else:
            site_profiles[profile['site']]['username'].append(profile)

    # Spawn scraping jobs
    for site, type_profiles in site_profiles.items():
        if site == 'twitter':
            chunk_size = 100
        else:
            chunk_size = 1
        # Break jobs into  API request type - username or ID
        for type_, t_profiles in type_profiles.items():
            # Chunk by API request size
            for i in range(0, len(t_profiles), chunk_size):
                chunk = t_profiles[i:i+chunk_size]
                if type_ == 'upstream_id':
                    ids = [i['upstream_id'] for i in chunk]
                    labels = _create_labels_dict(profiles=chunk, type_='upstream_id')
                    job = _scrape_queue.enqueue_call(
                        func=worker.scrape.scrape_profile_by_id,
                        args=(site, ids, stub, labels),
                        timeout=_redis_worker['profile_timeout']
                    )
                else:
                    usernames = [i['username'] for i in chunk]
                    labels = _create_labels_dict(profiles=chunk, type_='username')
                    job = _scrape_queue.enqueue_call(
                        func=worker.scrape.scrape_profile,
                        args=(site, usernames, stub, labels),
                        timeout=_redis_worker['profile_timeout']
                    )

                description = (
                    'Scraping bios for {} {} profiles'
                    .format(len(chunk), site)
                )

                worker.init_job(job=job, description=description)


def schedule_posts(profile, recent=True):
    """ Queue a job to get posts for the specified profile. """

    scrapers = {
        'instagram': worker.scrape.scrape_instagram_posts,
        'twitter': worker.scrape.scrape_twitter_posts,
    }

    description = 'Getting posts for "{}" on {}' \
                  .format(profile.username, profile.site_name())
    type_ = 'posts'

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
    """ Queue a job to get relations for the specified profile. """

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
    """ Schedule a determinate sleep task (useful for testing). """

    description = 'Determinate sleep for {} seconds'.format(period)

    job = _scrape_queue.enqueue(
        worker.sleep.sleep_determinate,
        period,
        timeout=period + 1
    )

    worker.init_job(job, description)


def schedule_sleep_exception(period):
    """ Schedule a sleep task that raises an exception (useful for testing). """

    description = 'Exception sleep for {} seconds'.format(period)

    job = _scrape_queue.enqueue(
        worker.sleep.sleep_exception,
        period,
        timeout=period + 1
    )

    worker.init_job(job, description)


def schedule_sleep_indeterminate(period):
    """ Schedule an indeterminate sleep task (useful for testing). """

    description = 'Indeterminate sleep for {} seconds'.format(period)

    job = _scrape_queue.enqueue(
        worker.sleep.sleep_indeterminate,
        period,
        timeout=period + 1
    )

    worker.init_job(job, description)

def _create_labels_dict(profiles, type_):
    """
    Create dictionary of labels from list of profiles.
    """

    labels = {}

    if type_ not in ['upstream_id', 'username']:
        raise ValueError('`type_` must be "upstream_id" or "username"')

    for profile in profiles:
        if 'labels' in profile:
            if type_ == 'username':
                key = profile[type_].lower()
            else:
                key = profile[type_]

            labels[key] = list(set(profile['labels']))

    return labels
