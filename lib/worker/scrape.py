''' Worker functions for performing scraping tasks asynchronously. '''

import bs4
from datetime import datetime
import dateutil.parser
import hashlib
import json
import os
import pickle
from urllib.parse import urlparse

import requests
import requests.exceptions
from sqlalchemy.exc import IntegrityError

import app.database
import app.index
import app.queue
from model import Avatar, Configuration, File, Post, Profile
from model.profile import profile_join_self
import worker
import worker.index


class ScrapeException(Exception):
    ''' Represents a user-facing exception. '''

    def __init__(self, message):
        self.message = message


def scrape_avatar(id_, site, url):
    '''
    Get an twitter avatar from ``url`` and save it to the Profile identified by
    ``id_``.
    '''

    worker.start_job()
    redis = worker.get_redis()
    db_session = worker.get_session()
    avatar = None
    profile = db_session.query(Profile).filter(Profile.id==id_).first()

    if profile is None:
        raise ValueError('No profile exists with id={}'.format(id_))

    if site == 'twitter':
        # Twitter points you to a scaled image by default, but we can
        # get the original resolution by removing "_normal" from the URL.
        #
        # See: https://dev.twitter.com/overview/general/user-profile-images-and-banners
        url = url.replace('_normal', '')

    # Update Avatar if it's already stored in the db
    for profile_avatar in profile.avatars:
        if profile_avatar.upstream_url == url:
            profile_avatar.end_date = datetime.today()
            avatar = profile_avatar

    # Otherwise, scrape the new Avatar and append to the profile
    if avatar is None:

        response = requests.get(url)
        response.raise_for_status()

        if 'content-type' in response.headers:
            mime = response.headers['content-type']
        else:
            mime = 'application/octet-stream'

        image = response.content
        avatar = Avatar(url, mime, image)
        profile.avatars.append(avatar)

    db_session.commit()
    worker.finish_job()

    redis.publish('avatar', json.dumps({
        'id': id_,
        'thumb_url': '/api/file/' + str(avatar.thumb_file.id),
        'url': '/api/file/' + str(avatar.file.id),
    }))


def scrape_profile(site, username):
    ''' Scrape a twitter or instagram account. '''

    redis = worker.get_redis()
    worker.start_job()

    try:
        if site == 'twitter':
            profile = scrape_twitter_account(username)
        elif site == 'instagram':
            profile = scrape_instagram_account(username)
        else:
            raise ScrapeException('No scraper exists for site: {}'.format(site))

        redis.publish('profile', json.dumps(profile))
        worker.finish_job()

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

def scrape_profile_by_id(site, upstream_id):
    ''' Scrape a twitter or instagram account using the user ID. '''

    redis = worker.get_redis()
    worker.start_job()

    try:
        if site == 'twitter':
            profile = scrape_twitter_account_by_id(upstream_id)
        elif site == 'instagram':
            profile = scrape_instagram_account_by_id(upstream_id)
        else:
            raise ScrapeException('No scraper exists for site: {}'.format(site))

        redis.publish('profile', json.dumps(profile))
        worker.finish_job()

    except requests.exceptions.HTTPError as he:
        response = he.response
        message = {'upstream_id': upstream_id, 'site': site, 'code': response.status_code}

        if response.status_code == 404:
            message['error'] = 'Does not exist on Twitter.'
        else:
            message['error'] = 'Cannot communicate with Twitter ({})' \
                               .format(response.status_code)

        redis.publish('profile', json.dumps(message))

    except ScrapeException as se:
        message = {
            'upstream_id': upstream_id,
            'site': site,
            'error': se.message,
        }
        redis.publish('profile', json.dumps(message))

    except Exception as e:
        message = {
            'upstream_id': upstream_id,
            'site': site,
            'error': 'Unknown error while fetching profile.',
        }
        redis.publish('profile', json.dumps(message))
        raise


def scrape_instagram_account(username):
    ''' Scrape instagram bio data and create (or update) a profile. '''

    # Getting a user ID is more difficult than it ought to be: you need to
    # search for the username and iterate through the search results results to
    # find an exact match.
    db_session = worker.get_session()
    proxies = _get_proxies(db_session)

    api_url = 'https://api.instagram.com/v1/users/search'
    params = {'q': username}

    response = requests.get(
        api_url,
        params=params,
        proxies=proxies,
        verify=False
    )

    response.raise_for_status()
    search_results = response.json()
    username_lower = username.lower()
    user_id = None

    for user_result in search_results['data']:
        if user_result['username'].lower() == username_lower:
            user_id = user_result['id']
            break

    if user_id is None:
        raise ScrapeException('Can\'t find Instagram user named {}.'
                              .format(username))

    # Now make another request to get this user's profile data.
    api_url = 'https://api.instagram.com/v1/users/{}'.format(user_id)

    response = requests.get(
        api_url,
        proxies=proxies,
        verify=False
    )

    response.raise_for_status()
    data = response.json()['data']
    profile = Profile('instagram', user_id, data['username'])
    db_session.add(profile)

    try:
        db_session.commit()
    except IntegrityError:
        # Already exists: use the existing profile.
        db_session.rollback()
        profile = db_session.query(Profile) \
                            .filter(Profile.site=='instagram') \
                            .filter(Profile.upstream_id==user_id) \
                            .one()

    profile.description = data['bio']
    profile.follower_count = int(data['counts']['followed_by'])
    profile.friend_count = int(data['counts']['follows'])
    profile.homepage = data['website']
    profile.name = data['full_name']
    profile.post_count = int(data['counts']['media'])
    profile.is_stub = False
    db_session.commit()

    # Schedule followup jobs.
    app.queue.schedule_avatar(profile, data['profile_picture'])
    app.queue.schedule_index_profile(profile)
    app.queue.schedule_posts(profile)
    app.queue.schedule_relations(profile)

    return profile.as_dict()

def scrape_instagram_account_by_id(upstream_id):
    ''' Scrape instagram bio data for upstream ID and update a profile. '''

    db_session = worker.get_session()
    proxies = _get_proxies(db_session)

    profile = db_session.query(Profile) \
                        .filter(Profile.site=='instagram') \
                        .filter(Profile.upstream_id==upstream_id) \
                        .one()

    # Instagram API request.
    api_url = 'https://api.instagram.com/v1/users/{}'.format(upstream_id)

    response = requests.get(
        api_url,
        proxies=proxies,
        verify=False
    )

    response.raise_for_status()
    data = response.json()['data']

    # Update profile
    profile.description = data['bio']
    profile.follower_count = int(data['counts']['followed_by'])
    profile.friend_count = int(data['counts']['follows'])
    profile.homepage = data['website']
    profile.name = data['full_name']
    profile.post_count = int(data['counts']['media'])
    profile.is_stub = False
    db_session.commit()

    # Schedule followup jobs.
    app.queue.schedule_avatar(profile, data['profile_picture'])
    app.queue.schedule_index_profile(profile)
    app.queue.schedule_posts(profile)
    app.queue.schedule_relations(profile)

    return profile.as_dict()

def scrape_instagram_posts(id_):
    '''
    Fetch posts for the user identified by id_.
    '''

    redis = worker.get_redis()
    db = worker.get_session()
    author = db.query(Profile).filter(Profile.id==id_).first()
    proxies = _get_proxies(db)
    min_id = None

    if author is None:
        raise ValueError('No profile exists with id={}'.format(id_))

    url = 'https://api.instagram.com/v1/users/{}/media/recent' \
          .format(author.upstream_id)

    # Get last post currently stored in db for this profile.
    last_post_query = db.query(Post) \
                        .filter(Post.author_id == id_) \
                        .order_by(Post.upstream_created.desc()) \
                        .first()

    # Only fetch posts later than the last_post
    if last_post_query is not None:
        min_id = last_post_query.upstream_id
        url = url + '?min_id={}'.format(min_id)

    response = requests.get(
        url,
        proxies=proxies,
        verify=False
    )

    response.raise_for_status()
    post_ids = list()
    response_json = response.json()['data']
    worker.start_job(total=len(response_json))
    current = 1

    # Instagram API result includes post with min_id so remove it
    response_json[:] = [d for d in response_json if d.get('id') != min_id]

    for gram in response_json:
        if gram['caption'] is not None:
            text = gram['caption']['text']
        else:
            text = None

        post = Post(
            author,
            gram['id'],
            datetime.fromtimestamp(int(gram['created_time'])),
            text
        )

        if gram['location'] is not None:
            if 'latitude' in gram['location']:
                post.latitude = gram['location']['latitude']
                post.longitude = gram['location']['longitude']

            post.location = gram['location']['name']

            if 'street_address' in gram['location']:
                post.location += ' ' + gram['location']['street_address']

        if 'images' in gram:
            image_url = gram['images']['standard_resolution']['url']
            name = os.path.basename(urlparse(image_url).path)
            img_response = requests.get(image_url, verify=False)
            mime = img_response.headers['Content-type']
            image = img_response.content
            post.attachments.append(File(name, mime, image))

        db.add(post)
        db.flush()
        post_ids.append(post.id)
        worker.update_job(current=current)
        current += 1

    db.commit()
    worker.finish_job()
    redis.publish('profile_posts', json.dumps({'id': id_}))
    app.queue.schedule_index_posts(post_ids)


def scrape_instagram_relations(id_):
    '''
    Fetch friends and followers for the Instagram user identified by `id_`.
    '''

    redis = worker.get_redis()
    db = worker.get_session()
    profile = db.query(Profile).filter(Profile.id==id_).first()
    proxies = _get_proxies(db)

    if profile is None:
        raise ValueError('No profile exists with id={}'.format(id_))

    # Get friends currently stored in db for this profile.
    friends_query = \
        db.query(Profile) \
            .join(\
                profile_join_self, \
                (profile_join_self.c.friend_id == Profile.id)
            )
    current_friends_ids = [friend.id for friend in friends_query]

    # Get followers currently stored in db for this profile.
    followers_query = \
        db.query(Profile.id) \
            .join(\
                profile_join_self, \
                (profile_join_self.c.follower_id == Profile.id)
            )
    current_followers_ids = [follower.id for follower in followers_query]

    # Get friend IDs.
    friends_url = 'https://api.instagram.com/v1/users/{}/follows' \
                  .format(profile.upstream_id)
    friends_response = requests.get(
        friends_url,
        proxies=proxies,
        verify=False
    )
    friends_response.raise_for_status()

    for friend in friends_response.json()['data']:
        # Only store friends that are not already in db.
        if friend['id'] not in current_friends_ids:
            related_profile = Profile(
                'instagram',
                friend['id'],
                friend['username'],
                is_stub=True
            )

            db.add(related_profile)

            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                related_profile = db \
                        .query(Profile) \
                        .filter(Profile.site=='instagram') \
                        .filter(Profile.upstream_id==friend['id']) \
                        .one()

            related_profile.name = friend['full_name']
            profile.friends.append(related_profile)

    # Get follower IDs.
    followers_url = 'https://api.instagram.com/v1/users/{}/followed-by' \
                    .format(profile.upstream_id)
    followers_response = requests.get(
        followers_url,
        proxies=proxies,
        verify=False
    )
    followers_response.raise_for_status()

    for follower in followers_response.json()['data']:
        # Only store followers that are not already in db.
        if follower['id'] not in current_followers_ids:
            related_profile = Profile(
                'instagram',
                follower['id'],
                follower['username'],
                is_stub=True
            )

            db.add(related_profile)

            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                related_profile = db \
                        .query(Profile) \
                        .filter(Profile.site=='instagram') \
                        .filter(Profile.upstream_id==follower['id']) \
                        .one()

            related_profile.name = follower['full_name']
            profile.followers.append(related_profile)


    worker.finish_job()
    redis.publish('profile_relations', json.dumps({'id': id_}))


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

    # Schedule followup jobs.
    app.queue.schedule_avatar(profile, data['profile_image_url_https'])
    app.queue.schedule_index_profile(profile)
    app.queue.schedule_posts(profile)
    app.queue.schedule_relations(profile)

    return profile.as_dict()

def scrape_twitter_account_by_id(upstream_id):
    '''
    Scrape twitter bio data for upstream ID and update a profile.
    Accepts twitter ID rather than username.
    '''

    db_session = worker.get_session()

    profile = db_session.query(Profile) \
                        .filter(Profile.site=='twitter') \
                        .filter(Profile.upstream_id==upstream_id) \
                        .one()

    # Request from Twitter API.
    api_url = 'https://api.twitter.com/1.1/users/lookup.json'
    params = {'user_id': upstream_id}
    response = requests.post(
        api_url,
        params=params,
        proxies=_get_proxies(db_session),
        verify=False
    )
    response.raise_for_status()

    # Update the profile.
    data = response.json()[0]
    _twitter_populate_profile(data, profile)
    profile.is_stub = False
    db_session.commit()

    # Schedule followup jobs.
    app.queue.schedule_avatar(profile, data['profile_image_url_https'])
    app.queue.schedule_index_profile(profile)
    app.queue.schedule_posts(profile)
    app.queue.schedule_relations(profile)

    return profile.as_dict()



def scrape_twitter_posts(id_):
    '''
    Fetch tweets for the user identified by id_.
    '''

    worker.start_job()
    redis = worker.get_redis()
    db = worker.get_session()
    author = db.query(Profile).filter(Profile.id==id_).first()

    if author is None:
        raise ValueError('No profile exists with id={}'.format(id_))

    # Get posts currently stored in db for this profile.
    post_query = db.query(Post) \
                        .filter(Post.author_id == id_) \
                        .order_by(Post.upstream_created.desc())

    url = 'https://api.twitter.com/1.1/statuses/user_timeline.json'
    params = {'count': 200, 'user_id': author.upstream_id}
    # Only fetch posts newer than those already stored in db
    if post_query.count() > 0:
        last_post_id = post_query[0].upstream_id
        params['since_id'] = last_post_id

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
    worker.finish_job()
    redis.publish('profile_posts', json.dumps({'id': id_}))
    app.queue.schedule_index_posts(post_ids)


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

    # Get friends currently stored in db for this profile.
    friends_query = \
        db.query(Profile) \
            .join(\
                profile_join_self, \
                (profile_join_self.c.friend_id == Profile.id)
            )
    current_friends_ids = [friend.id for friend in friends_query]


    # Get followers currently stored in db for this profile.
    followers_query = \
        db.query(Profile.id) \
            .join(\
                profile_join_self, \
                (profile_join_self.c.follower_id == Profile.id)
            )
    current_followers_ids = [follower.id for follower in followers_query]

    ## Get friend IDs.
    friends_url = 'https://api.twitter.com/1.1/friends/ids.json'
    friends_response = requests.get(
        friends_url,
        params=params,
        proxies=_get_proxies(db),
        verify=False
    )
    friends_response.raise_for_status()
    friends_ids = friends_response.json()['ids']
    # Ignore friends already in the db
    friends_ids = list(set(friends_ids) - set(current_friends_ids))

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
    # Ignore followers already in the db
    followers_ids = list(set(followers_ids) - set(current_followers_ids))

    # Get username for each of the friend/follower IDs and create
    # a relationship in QuickPin.
    user_ids = [(uid, 'friend') for uid in friends_ids] + \
               [(uid, 'follower') for uid in followers_ids]

    worker.start_job(total=len(user_ids))
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

        worker.update_job(current=chunk_end)

    db.commit()
    worker.finish_job()
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
    profile.homepage = dict_['url']
    profile.join_date = dateutil.parser.parse(dict_['created_at'])
    profile.location = dict_['location']
    profile.name = dict_['name']
    profile.post_count = dict_['statuses_count']
    profile.private = dict_['protected']
    profile.time_zone = dict_['time_zone']
