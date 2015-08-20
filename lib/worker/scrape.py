''' Worker functions for performing scraping tasks asynchronously. '''

import bs4
from datetime import datetime
import dateutil.parser
import hashlib
import json
import pickle
import urllib.parse

import requests
import requests.exceptions
from sqlalchemy.exc import IntegrityError

import app.database
import app.index
import app.queue
from model import Configuration, File, Post, Profile
import worker
import worker.index


class ScrapeException(Exception):
    ''' Represents a user-facing exception. '''

    def __init__(self, message):
        self.message = message


def scrape_account(site, username):
    ''' Scrape a twitter account. '''

    redis = worker.get_redis()

    try:
        profile = _scrape_twitter_account(username)
        redis.publish('profile', json.dumps(profile))

    except requests.exceptions.HTTPError as he:
        response = he.response
        message = {'username': username, 'site': site, 'code': response.status_code}

        if response.status_code == 404:
            message['error'] = 'Does not exist on Twitter.'
        else:
            message['error'] = 'Cannot communicate with Twitter ({})' \
                               .format(response.status_code)

        redis.publish('profile', json.dumps(message))

    except ScrapeException as se:
        message = {
            'username': username,
            'site': site,
            'error': se.message,
        }
        redis.publish('profile', json.dumps(message))

    except Exception as e:
        message = {
            'username': username,
            'site': site,
            'error': 'Unknown error while fetching profile.',
        }
        redis.publish('profile', json.dumps(message))
        raise


def _get_proxies(db):
    ''' Get a dictionary of proxy information from the app configuration. '''

    piscina_url = db.query(Configuration) \
                    .filter(Configuration.key=='piscina_proxy_url') \
                    .first()

    if piscina_url is None or piscina_url.value.strip() == '':
        raise ScrapeException('No Piscina server configured.')

    return {
        'http': piscina_url.value,
        'https': piscina_url.value,
    }


def _scrape_twitter_account(username):
    '''
    Scrape twitter bio data and create (or update) a profile.

    TODO The API call used here supports up to 100 usernames at a time. We
    could easily modify this function to populate many profiles at once.
    '''

    # Request from Twitter API.
    db_session = worker.get_session()

    api_url = 'https://api.twitter.com/1.1/users/lookup.json'
    params = {'screen_name': username}
    response = requests.get(
        api_url,
        params=params,
        proxies=_get_proxies(db_session),
        verify=False
    )
    response.raise_for_status()

    # Get Twitter ID and upsert the profile.
    data = response.json()[0] # TODO Only supports getting 1 profile right now...
    user_id = data['id_str']
    profile = Profile('twitter', user_id, username)
    db_session.add(profile)

    try:
        db_session.commit()
    except IntegrityError:
        # Already exists: use the existing profile.
        db_session.rollback()
        profile = db_session.query(Profile) \
                            .filter(Profile.site=='twitter') \
                            .filter(Profile.upstream_id==user_id) \
                            .one()

    profile.description = data['description']
    profile.follower_count = data['followers_count']
    profile.friend_count = data['friends_count']
    profile.join_date = dateutil.parser.parse(data['created_at'])
    profile.location = data['location']
    profile.name = data['name']
    profile.username = data['screen_name']
    profile.post_count = data['statuses_count']
    profile.private = data['protected']
    profile.time_zone = data['time_zone']

    db_session.commit()

    # Schedule follow up jobs.
    avatar_job = app.queue.scrape_queue.enqueue(
        scrape_twitter_avatar,
        profile.id,
        data['profile_image_url_https']
    )
    avatar_job.meta['description'] = 'Getting avatar image for "{}" on "{}"' \
                                     .format(username, 'twitter')
    avatar_job.save()

    index_job = app.queue.index_queue.enqueue(worker.index.index_profile, profile.id)
    index_job.meta['description'] = 'Indexing profile "{}" on "{}"' \
                                    .format(username, 'twitter')
    index_job.save()

    posts_job = app.queue.scrape_queue.enqueue(scrape_twitter_posts, profile.id)
    posts_job.meta['description'] = 'Getting posts for "{}" on "{}"' \
                                    .format(username, 'twitter')
    posts_job.save()

    return profile.as_dict()


def scrape_twitter_avatar(id_, url):
    '''
    Get a twitter avatar from ``url`` and save it to the Profile identified by
    ``id_``.
    '''

    redis = worker.get_redis()
    db_session = worker.get_session()

    profile = db_session.query(Profile).filter(Profile.id==id_).first()

    if profile is None:
        raise ValueError('No profile exists with id={}'.format(id_))

    # Twitter points you to a scaled image by default, but we can get the
    # original resolution by removing "_normal" from the URL.
    #
    # See: https://dev.twitter.com/overview/general/user-profile-images-and-banners
    url = url.replace('_normal', '')
    response = requests.get(url, stream=True)
    response.raise_for_status()
    parsed = urllib.parse.urlparse(url)
    name = url.split('/')[-1]

    if 'content-type' in response.headers:
        mime = response.headers['content-type']
    else:
        mime = 'application/octet-stream'

    content = response.raw.read()
    file_ = File(name=name, mime=mime, content=content)
    profile.avatars.append(file_)
    db_session.commit()
    redis.publish('avatar', json.dumps({'id': id_, 'url': '/api/file/' + str(file_.id)}))


def scrape_twitter_posts(id_):
    '''
    Fetch tweets for the user identified by id_.
    '''

    redis = worker.get_redis()
    db = worker.get_session()
    author = db.query(Profile).filter(Profile.id==id_).first()

    if author is None:
        raise ValueError('No profile exists with id={}'.format(id_))

    url = 'https://api.twitter.com/1.1/statuses/user_timeline.json'
    params = {'count': 200, 'user_id': author.upstream_id}
    response = requests.get(
        url,
        params=params,
        proxies=_get_proxies(db),
        verify=False
    )
    response.raise_for_status()

    for tweet in response.json():
        post = Post(
            author,
            tweet['id_str'],
            dateutil.parser.parse(tweet['created_at']),
            tweet['text']
        )

        if tweet['lang'] is not None:
            post.language = tweet['lang']

        if tweet['coordinates'] is not None:
            post.latitude, post.longitude = tweet['coordinates']

        db.add(post)

    db.commit()
    redis.publish('profile_posts', json.dumps({'id': id_}))
