''' Worker functions for performing scraping tasks asynchronously. '''

import bs4
from datetime import datetime
import dateutil.parser
import hashlib
import json
import os
import pickle

import requests
import requests.exceptions
from sqlalchemy.exc import IntegrityError

import app.database
import app.index
import app.queue
from model import Avatar, Configuration, Post, Profile
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
        profile = scrape_twitter_account(username)
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


def scrape_twitter_account(username):
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
    profile = Profile('twitter', user_id, data['screen_name'])
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

    _twitter_populate_profile(data, profile)
    profile.is_stub = False
    db_session.commit()

    # Schedule avatar image followup job.
    avatar_job = app.queue.scrape_queue.enqueue(
        scrape_twitter_avatar,
        profile.id,
        data['profile_image_url_https']
    )
    avatar_desc = 'Getting avatar image for "{}" on "{}"' \
                  .format(profile.username, profile.site_name())
    avatar_job.meta['description'] = avatar_desc
    avatar_job.save()

    # Schedule search index followup job.
    index_job = app.queue.index_queue.enqueue(
        worker.index.index_profile,
        profile.id
    )
    index_desc = 'Indexing profile "{}" on "{}"' \
                 .format(profile.username, profile.site_name())
    index_job.meta['description'] = index_desc
    index_job.save()

    # Schedule scrape posts followup job.
    posts_job = app.queue.scrape_queue.enqueue(
        scrape_twitter_posts,
        profile.id
    )
    posts_desc = 'Getting posts for "{}" on "{}"' \
                 .format(profile.username, profile.site_name())
    posts_job.meta['description'] = posts_desc
    posts_job.save()

    # Schedule scrape relations followup job.
    relations_job = app.queue.scrape_queue.enqueue(
        scrape_twitter_relations,
        profile.id,
        timeout=3600
    )
    relations_desc = 'Getting friends & followers for "{}" on "{}"' \
                     .format(profile.username, profile.site_name())
    relations_job.meta['description'] = relations_desc
    relations_job.save()

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

    if 'content-type' in response.headers:
        mime = response.headers['content-type']
    else:
        mime = 'application/octet-stream'

    image = response.raw.read()
    avatar = Avatar(url, mime, image)
    profile.avatars.append(avatar)
    db_session.commit()
    redis.publish('avatar', json.dumps({
        'id': id_,
        'thumb_url': '/api/file/' + str(avatar.thumb_file.id),
        'url': '/api/file/' + str(avatar.file.id),
    }))


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

    post_ids = list()

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

        place = tweet['place']

        if place is not None:
            # Set longitude/latitude to the center the of bounding polygon.
            total_lon = 0
            total_lat = 0
            num_coords = 0

            for lon, lat in place['bounding_box']['coordinates'][0]:
                total_lon += lon
                total_lat += lat
                num_coords += 1

            post.longitude = total_lon / num_coords
            post.latitude = total_lat / num_coords

            # Set location to string identifying the place.
            post.location = '{}, {}'.format(
                place['full_name'],
                place['country']
            )

        db.add(post)
        db.flush()
        post_ids.append(post.id)

    db.commit()
    redis.publish('profile_posts', json.dumps({'id': id_}))

    # Schedule follow up jobs.
    index_job = app.queue.index_queue.enqueue(worker.index.index_posts, post_ids)
    index_job.meta['description'] = 'Indexing posts by {} on {}' \
                                    .format(author.username, author.site_name())
    index_job.save()


def scrape_twitter_relations(id_):
    '''
    Fetch friends and followers for the Twitter user identified by `id_`.

    Currently only gets the first "page" from each endpoint, e.g. 5000 friends
    and 5000 followers, because it's simpler and saves API calls.
    '''

    redis = worker.get_redis()
    db = worker.get_session()
    profile = db.query(Profile).filter(Profile.id==id_).first()

    if profile is None:
        raise ValueError('No profile exists with id={}'.format(id_))

    params = {
        'count': 5000,
        'user_id': profile.upstream_id,
        'stringify_ids': True
    }

    # Get friend IDs.
    friends_url = 'https://api.twitter.com/1.1/friends/ids.json'
    friends_response = requests.get(
        friends_url,
        params=params,
        proxies=_get_proxies(db),
        verify=False
    )
    friends_response.raise_for_status()
    friends_ids = friends_response.json()['ids']

    # Get follower IDs.
    followers_url = 'https://api.twitter.com/1.1/followers/ids.json'
    followers_response = requests.get(
        followers_url,
        params=params,
        proxies=_get_proxies(db),
        verify=False
    )
    followers_response.raise_for_status()
    followers_ids = followers_response.json()['ids']

    # Get username for each of the friend/follower IDs and create
    # a relationship in QuickPin.
    user_ids = [(uid, 'friend') for uid in friends_ids] + \
               [(uid, 'follower') for uid in followers_ids]

    chunk_size = 100
    for chunk_start in range(0, len(user_ids), chunk_size):
        chunk_end = chunk_start + chunk_size - 1
        chunk = user_ids[chunk_start:chunk_end]
        chunk_lookup = {id_:relation for id_,relation in chunk}

        lookup_url = 'https://api.twitter.com/1.1/users/lookup.json'
        lookup_response = requests.post(
            lookup_url,
            proxies=_get_proxies(db),
            verify=False,
            data={'user_id': ','.join(chunk_lookup.keys())}
        )
        lookup_response.raise_for_status()
        relations = lookup_response.json()

        for related_dict in relations:
            uid = related_dict['id_str']
            username = related_dict['screen_name']
            related_profile = Profile('twitter', uid, username, is_stub=True)
            db.add(related_profile)

            try:
                db.commit()
            except IntegrityError:
                # Already exists: use the existing profile.
                db.rollback()
                related_profile = db \
                    .query(Profile) \
                    .filter(Profile.site=='twitter') \
                    .filter(Profile.upstream_id==uid) \
                    .one()

            _twitter_populate_profile(related_dict, related_profile)
            relation = chunk_lookup[uid]

            if relation == 'friend':
                profile.friends.append(related_profile)
            else: # relation == 'follower':
                profile.followers.append(related_profile)

            db.commit()

    db.commit()
    redis.publish('profile_relations', json.dumps({'id': id_}))


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


def _twitter_populate_profile(dict_, profile):
    '''
    Copy attributes from `dict_`, a `/users/lookup` API response, into a
    `Profile` instance.
    '''

    profile.description = dict_['description']
    profile.follower_count = dict_['followers_count']
    profile.friend_count = dict_['friends_count']
    profile.join_date = dateutil.parser.parse(dict_['created_at'])
    profile.location = dict_['location']
    profile.name = dict_['name']
    profile.post_count = dict_['statuses_count']
    profile.private = dict_['protected']
    profile.time_zone = dict_['time_zone']
