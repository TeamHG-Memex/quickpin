""" Worker functions for performing scraping tasks asynchronously. """

import bs4
from datetime import datetime
import dateutil.parser
import json
import os
from urllib.parse import urlparse

import requests
import requests.exceptions
from sqlalchemy.exc import IntegrityError

import app.database
import app.index
import app.queue
from model import Avatar, File, Post, Profile, Label
from model.profile import profile_join_self
from model.configuration import get_config
import worker
import worker.index


class ScrapeException(Exception):
    """ Represents a user-facing exception. """

    def __init__(self, message):
        self.message = message


def scrape_avatar(id_, site, url):
    """
    Get an twitter avatar from ``url`` and save it to the Profile identified by
    ``id_``.
    """

    worker.start_job()
    redis = worker.get_redis()
    db_session = worker.get_session()
    avatar = None
    profile = db_session.query(Profile).filter(Profile.id == id_).first()

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


def scrape_profile(site, usernames, stub=False, labels={}):
    """ Scrape a twitter or instagram account. """

    redis = worker.get_redis()
    worker.start_job()

    try:
        if site == 'twitter':
            profiles = scrape_twitter_account(usernames, stub, labels)
        elif site == 'instagram':
            profiles = []
            for username in usernames:
                profile = scrape_instagram_account(username, stub)
                profiles.append(profile)
        else:
            raise ScrapeException('No scraper exists for site: {}'.format(site))

        for profile in profiles:
            redis.publish('profile', json.dumps(profile))

        worker.finish_job()

    except requests.exceptions.HTTPError as he:
        response = he.response
        message = {
            'usernames': usernames,
            'site': site,
            'code': response.status_code
        }

        if response.status_code == 404:
            message['error'] = 'Does not exist on Twitter.'
        else:
            message['error'] = 'Cannot communicate with Twitter ({})' \
                               .format(response.status_code)

        redis.publish('profile', json.dumps(message))

    except ScrapeException as se:
        message = {
            'usernames': usernames,
            'site': site,
            'error': se.message,
        }
        redis.publish('profile', json.dumps(message))

    except:
        message = {
            'usernames': usernames,
            'site': site,
            'error': 'Unknown error while fetching profile.',
        }
        redis.publish('profile', json.dumps(message))
        raise


def scrape_profile_by_id(site, upstream_ids, stub=False, labels={}):
    """ Scrape a twitter or instagram account using the user ID. """

    redis = worker.get_redis()
    worker.start_job()

    try:
        if site == 'twitter':
            profiles = scrape_twitter_account_by_id(upstream_ids, stub, labels)
        elif site == 'instagram':
            profiles = []
            for upstream_id in upstream_ids:
                profile = scrape_instagram_account(upstream_id, stub)
                profiles.append(profile)
        else:
            raise ScrapeException('No scraper exists for site: {}'.format(site))

        for profile in profiles:
            redis.publish('profile', json.dumps(profile))

        worker.finish_job()

    except requests.exceptions.HTTPError as he:
        response = he.response
        message = {'upstream_ids': upstream_ids, 'site': site, 'code': response.status_code}

        if response.status_code == 404:
            message['error'] = 'Does not exist on Twitter.'
        else:
            message['error'] = 'Cannot communicate with Twitter ({})' \
                               .format(response.status_code)

        redis.publish('profile', json.dumps(message))

    except ScrapeException as se:
        message = {
            'upstream_ids': upstream_ids,
            'site': site,
            'error': se.message,
        }
        redis.publish('profile', json.dumps(message))

    except:
        message = {
            'upstream_ids': upstream_ids,
            'site': site,
            'error': 'Unknown error while fetching profile.',
        }
        redis.publish('profile', json.dumps(message))
        raise


def scrape_instagram_account(username, stub=False):
    """ Scrape instagram bio data and create (or update) a profile. """
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
                            .filter(Profile.site == 'instagram') \
                            .filter(Profile.upstream_id == user_id) \
                            .one()

    profile.last_update = datetime.now()
    profile.description = data['bio']
    profile.follower_count = int(data['counts']['followed_by'])
    profile.friend_count = int(data['counts']['follows'])
    profile.homepage = data['website']
    profile.name = data['full_name']
    profile.post_count = int(data['counts']['media'])
    profile.is_stub = stub
    db_session.commit()

    # Schedule followup jobs.
    app.queue.schedule_index_profile(profile) # index all profiles, inc stubs
    if not stub:
        app.queue.schedule_avatar(profile, data['profile_picture'])
        app.queue.schedule_posts(profile, recent=True)
        app.queue.schedule_relations(profile)

    return profile.as_dict()


def scrape_instagram_account_by_id(upstream_id, stub=False):
    """ Scrape instagram bio data for upstream ID and update a profile. """

    db_session = worker.get_session()
    proxies = _get_proxies(db_session)

    # Instagram API request.
    api_url = 'https://api.instagram.com/v1/users/{}'.format(upstream_id)

    response = requests.get(
        api_url,
        proxies=proxies,
        verify=False
    )

    response.raise_for_status()
    data = response.json()['data']

    # Update the profile.
    data = response.json()[0]
    profile = Profile('instagram', upstream_id, data['screen_name'])
    db_session.add(profile)

    try:
        db_session.commit()
    except IntegrityError:
        # Already exists: use the existing profile.
        db_session.rollback()
        profile = db_session.query(Profile) \
                            .filter(Profile.site == 'instagram') \
                            .filter(Profile.upstream_id == upstream_id) \
                            .one()

    # Update profile
    profile.last_update = datetime.now()
    profile.description = data['bio']
    profile.follower_count = int(data['counts']['followed_by'])
    profile.friend_count = int(data['counts']['follows'])
    profile.homepage = data['website']
    profile.name = data['full_name']
    profile.post_count = int(data['counts']['media'])
    profile.is_stub = stub
    db_session.commit()

    # Schedule followup jobs.
    app.queue.schedule_index_profile(profile) # index all profiles, inc stubs
    if not stub:
        app.queue.schedule_avatar(profile, data['profile_picture'])
        app.queue.schedule_posts(profile, recent=True)
        app.queue.schedule_relations(profile)

    return profile.as_dict()


def scrape_instagram_posts(id_, recent):
    """
    Fetch instagram posts for the user identified by id_.
    Checks posts already stored in db, and will only fetch older or newer
    posts depending on value of the boolean argument 'recent',
    e.g. recent=True will return recent posts not already stored in the db.
    The number of posts to fetch is configured in the Admin.
    """
    redis = worker.get_redis()
    db = worker.get_session()
    author = db.query(Profile).filter(Profile.id == id_).first()
    proxies = _get_proxies(db)
    max_results = get_config(db, 'max_posts_instagram', required=True).value
    try:
        max_results = int(max_results)
    except:
        raise ScrapeException('Value of max_posts_instagram must be an integer')

    min_id = None
    results = 0
    params = {}

    if author is None:
        raise ValueError('No profile exists with id={}'.format(id_))

    url = 'https://api.instagram.com/v1/users/{}/media/recent' \
          .format(author.upstream_id)

    # Get last post currently stored in db for this profile.
    post_query = db.query(Post) \
        .filter(Post.author_id == id_) \
        .order_by(Post.upstream_created.desc()) \

    if post_query.count() > 0:
        # Only fetch posts newer than those already stored in db
        if recent:
            min_id = post_query[0].upstream_id
            params['min_id'] = str(min_id)
        # Only fetch posts older than those already stored in db
        else:
            max_id = post_query[post_query.count() - 1].upstream_id
            params['max_id'] = str(max_id)

    worker.start_job(total=max_results)
    while results < max_results:
        response = requests.get(
            url,
            params=params,
            proxies=proxies,
            verify=False
        )

        response.raise_for_status()
        post_ids = list()
        response_json = response.json()['data']
        pagination = response.json()['pagination']

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

                if 'name' in gram['location']:
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
            worker.update_job(current=results)
            results += 1
            if results == max_results:
                break

        # If there are more results, set the max_id param, otherwise finish
        if 'next_max_id' in pagination:
            params['max_id'] = pagination['next_max_id']
        else:
            break

    db.commit()
    worker.finish_job()
    redis.publish('profile_posts', json.dumps({'id': id_}))
    app.queue.schedule_index_posts(post_ids)


def scrape_instagram_relations(id_):
    """
    Fetch friends and followers for the Instagram user identified by `id_`.
    The number of friends and followers to fetch is configured in Admin.
    """
    redis = worker.get_redis()
    db = worker.get_session()
    profile = db.query(Profile).filter(Profile.id==id_).first()
    proxies = _get_proxies(db)
    friends_results = 0
    followers_results = 0
    max_results = get_config(db, 'max_relations_instagram', required=True).value

    try:
        max_results = int(max_results)
    except:
        raise ScrapeException(
            'Value of max_relations_instagram must be an integer'
        )

    friends_params = {}
    followers_params = {}
    total_results = max_results*2

    if profile is None:
        raise ValueError('No profile exists with id={}'.format(id_))

    # Get friends currently stored in db for this profile.
    friends_query = \
        db.query(Profile.upstream_id) \
            .join(\
                profile_join_self, \
                (profile_join_self.c.friend_id == Profile.id)
            ) \
            .filter(profile_join_self.c.follower_id == id_)
    current_friends_ids = [friend.upstream_id for friend in friends_query]

    # Get followers currently stored in db for this profile.
    followers_query = \
        db.query(Profile.upstream_id) \
            .join(\
                profile_join_self, \
                (profile_join_self.c.follower_id == Profile.id)
            ) \
            .filter(profile_join_self.c.friend_id == id_)
    current_followers_ids = [follower.upstream_id for follower in followers_query]

    worker.start_job(total=total_results)

    # Get friend IDs.
    friends_url = 'https://api.instagram.com/v1/users/{}/follows' \
                  .format(profile.upstream_id)

    while friends_results < max_results:
        # Get friends from Instagram API
        friends_response = requests.get(
            friends_url,
            params=friends_params,
            proxies=proxies,
            verify=False
        )
        friends_response.raise_for_status()
        pagination = friends_response.json()['pagination']

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
                friends_results += 1
                worker.update_job(current=friends_results)

                if friends_results == max_results:
                    break

        # If there are more results, set the cursor paramater, otherwise finish
        if 'next_cursor' in pagination:
            friends_params['cursor'] = pagination['next_cursor']
        else:
            break # No more results

    # Get follower IDs.
    followers_url = 'https://api.instagram.com/v1/users/{}/followed-by' \
                    .format(profile.upstream_id)

    # Get followers from Instagram API
    while followers_results < max_results:
        # Get friends from Instagram API
        followers_response = requests.get(
            followers_url,
            params=followers_params,
            proxies=proxies,
            verify=False
        )
        followers_response.raise_for_status()
        pagination = followers_response.json()['pagination']

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
                followers_results += 1
                worker.update_job(current=friends_results + followers_results)

                if followers_results == max_results:
                    break

        # If there are more results, set the cursor paramater, otherwise finish
        if 'next_cursor' in pagination:
            followers_params['cursor'] = pagination['next_cursor']
        else:
            break # No more results

    worker.finish_job()
    redis.publish('profile_relations', json.dumps({'id': id_}))


def scrape_twitter_account(usernames, stub=False, labels=None):
    """
    Scrape twitter bio data and create (or update) a list of profile
    usernames.

    Keyword arguments:
    stub -- add the profile in stub mode (default False)
    labels -- dictionary of username labels (default None)
    """

    if len(usernames) > 100:
        raise ScrapeException('Twitter API max is 100 user IDs per request.')

    profiles = []
    # Request from Twitter API.
    db_session = worker.get_session()

    api_url = 'https://api.twitter.com/1.1/users/lookup.json'
    payload = {'screen_name': ','.join(usernames)}
    response = requests.post(
        api_url,
        data=payload,
        proxies=_get_proxies(db_session),
        verify=False
    )
    response.raise_for_status()

    # Get Twitter ID and upsert the profile.
    for profile_json in response.json():
        user_id = profile_json['id_str']
        profile = Profile('twitter', user_id, profile_json['screen_name'])
        profile.is_stub = stub
        profile.private = profile_json['protected']
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

        _twitter_populate_profile(profile_json, profile)

        if profile.username.lower() in labels:
            print('Labels: {}'.format(labels), flush=True)
            _label_profile(db_session, profile, labels[profile.username.lower()])

        profile.last_update = datetime.now()
        db_session.commit()
        profiles.append(profile.as_dict())

        # Schedule followup jobs.
        app.queue.schedule_index_profile(profile)

        if not stub:
            app.queue.schedule_avatar(profile, profile_json['profile_image_url_https'])

            # Only get tweets and relations for unprotected profiles
            if not profile.private:
                app.queue.schedule_posts(profile, recent=True)
                app.queue.schedule_relations(profile)

    return profiles


def scrape_twitter_account_by_id(upstream_ids, stub=False, labels={}):
    """
    Scrape twitter bio data for upstream IDs and/or updates a profile.
    Accepts twitter ID rather than username.
    """
    if len(upstream_ids) > 100:
        raise ScrapeException('Twitter API max is 100 user IDs per request.')

    db_session = worker.get_session()
    profiles = []

    # Request from Twitter API.
    api_url = 'https://api.twitter.com/1.1/users/lookup.json'
    payload = {'user_id': ','.join(upstream_ids)}
    response = requests.post(
        api_url,
        data=payload,
        proxies=_get_proxies(db_session),
        verify=False
    )
    response.raise_for_status()

    # Update the profile.
    for profile_json in response.json():
        profile = Profile(
            'twitter',
            profile_json['id_str'],
            profile_json['screen_name']
        )
        profile.is_stub = stub
        profile.private = profile_json['protected']
        db_session.add(profile)

        try:
            db_session.commit()
        except IntegrityError:
            # Already exists: use the existing profile.
            db_session.rollback()
            profile = db_session.query(Profile) \
                                .filter(Profile.site=='twitter') \
                                .filter(
                                    Profile.upstream_id==profile_json['id_str']
                                )\
                                .one()
            # Profiles already in the system are either not stubs or
            # being updated to full profiles
            profile.is_stub = False


        _twitter_populate_profile(profile_json, profile)

        if profile.upstream_id in labels:
            _label_profile(db_session, profile, labels[profile.upstream_id])

        profile.last_update = datetime.now()
        db_session.commit()
        profiles.append(profile.as_dict())

        # Schedule followup jobs.
        app.queue.schedule_index_profile(profile)
        if not stub:
            app.queue.schedule_avatar(
                profile, profile_json['profile_image_url_https']
            )
            # Only get tweets and relations for unprotected profiles
            if not profile.private:
                app.queue.schedule_posts(profile, recent=True)
                app.queue.schedule_relations(profile)

    return profiles



def scrape_twitter_posts(id_, recent):
    """
    Fetch tweets for the user identified by id_.
    Checks tweets already stored in db, and will only fetch older or newer
    tweets depending on value of the boolean argument 'recent',
    e.g. recent=True will return recent tweets not already stored in the db.
    The number of tweets to fetch is configured in the Admin.
    """
    db = worker.get_session()
    max_results = get_config(db, 'max_posts_twitter', required=True).value

    try:
        max_results = int(max_results)
    except:
        raise ScrapeException('Value of max_posts_twitter must be an integer')

    worker.start_job(total=max_results)
    redis = worker.get_redis()
    author = db.query(Profile).filter(Profile.id==id_).first()
    proxies = _get_proxies(db)
    results = 0
    max_id = None
    more_results = True
    count = 200

    if author is None:
        raise ValueError('No profile exists with id={}'.format(id_))

    # Get posts currently stored in db for this profile.
    post_query = db.query(Post) \
                        .filter(Post.author_id == id_) \
                        .order_by(Post.upstream_created.desc())

    url = 'https://api.twitter.com/1.1/statuses/user_timeline.json'
    params = {'count': count, 'user_id': author.upstream_id}

    if post_query.count() > 0:
        # Only fetch posts newer than those already stored in db
        if recent:
            since_id = post_query[0].upstream_id
            params['since_id'] = str(since_id)
        # Only fetch posts older than those already stored in db
        else:
            max_id = post_query[post_query.count() -1].upstream_id
            params['max_id'] = str(max_id)

    while more_results:
        response = requests.get(
            url,
            params=params,
            proxies=proxies,
            verify=False
        )
        response.raise_for_status()

        post_ids = list()

        tweets = response.json()
        if len(tweets) == 0:
            more_results = False

        if len(tweets) < count:
            more_results = False

        for tweet in tweets:
            # Twitter API result set includes the tweet with the max_id/since_id
            # so ignore it.
            if tweet['id_str'] != max_id:
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
                # Set the max_id to the last tweet to get the next set of
                # results
                max_id = tweet['id_str']
                params['max_id'] = max_id
                results += 1
                worker.update_job(current=results)

                if results == max_results:
                    more_results = False
                    break


    db.commit()
    worker.finish_job()
    redis.publish('profile_posts', json.dumps({'id': id_}))
    app.queue.schedule_index_posts(post_ids)


def scrape_twitter_relations(id_):
    """
    Fetch friends and followers for the Twitter user identified by `id_`.
    The number of friends and followers to fetch is configured in Admin.
    """
    redis = worker.get_redis()
    db = worker.get_session()
    profile = db.query(Profile).filter(Profile.id==id_).first()
    proxies = _get_proxies(db)
    max_results = get_config(db, 'max_relations_twitter', required=True).value

    try:
        max_results = int(max_results)
    except:
        raise ScrapeException(
            'Value of max_relations_twitter must be an integer'
        )

    friends_results = 0
    friends_ids = []
    followers_results = 0
    followers_ids = []
    friends_cursor = -1
    followers_cursor = -1

    if profile is None:
        raise ValueError('No profile exists with id={}'.format(id_))

    params = {
        'count': 5000,
        'user_id': profile.upstream_id,
        'stringify_ids': True,
    }

    # Get friends currently stored in db for this profile.
    friends_query = \
        db.query(Profile.upstream_id) \
            .join(\
                profile_join_self, \
                (profile_join_self.c.friend_id == Profile.id)
            ) \
            .filter(profile_join_self.c.follower_id == id_)
    current_friends_ids = [friend.upstream_id for friend in friends_query]


    # Get followers currently stored in db for this profile.
    followers_query = \
        db.query(Profile.upstream_id) \
            .join(\
                profile_join_self, \
                (profile_join_self.c.follower_id == Profile.id)
            ) \
            .filter(profile_join_self.c.friend_id == id_)
    current_followers_ids = [follower.upstream_id for follower in followers_query]

    ## Get friend IDs.
    friends_url = 'https://api.twitter.com/1.1/friends/ids.json'
    params['cursor'] = friends_cursor

    while friends_results < max_results:
        friends_response = requests.get(
            friends_url,
            params=params,
            proxies=proxies,
            verify=False
        )
        friends_response.raise_for_status()

        # Ignore friends already in the db
        for friend_id in friends_response.json()['ids']:
            if friend_id not in current_friends_ids:
                friends_ids.append(friend_id)
                friends_results += 1
                if friends_results == max_results:
                    break

        friends_cursor = friends_response.json()['next_cursor']

        if friends_cursor == 0:
            break # No more results
        else:
            params['cursor'] = friends_cursor

    # Get follower IDs.
    followers_url = 'https://api.twitter.com/1.1/followers/ids.json'
    params['cursor'] = followers_cursor

    while followers_results < max_results:
        followers_response = requests.get(
            followers_url,
            params=params,
            proxies=proxies,
            verify=False
        )
        followers_response.raise_for_status()

        # Ignore followers already in the db
        for follower_id in followers_response.json()['ids']:
            if follower_id not in current_followers_ids:
                followers_ids.append(follower_id)
                followers_results += 1
                if followers_results == max_results:
                    break

        followers_cursor = followers_response.json()['next_cursor']

        if followers_cursor == 0:
            break # No more results
        else:
            params['cursor'] = followers_cursor

    # Get username for each of the friend/follower IDs and create
    # a relationship in QuickPin.
    user_ids = [(uid, 'friend') for uid in friends_ids] + \
               [(uid, 'follower') for uid in followers_ids]
    worker.start_job(total=len(user_ids))
    chunk_size = 100
    for chunk_start in range(0, len(user_ids), chunk_size):
        chunk_end = chunk_start + chunk_size
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
    """ Get a dictionary of proxy information from the app configuration. """

    piscina_url = get_config(db, 'piscina_proxy_url', required=True)

    if piscina_url is None or piscina_url.value.strip() == '':
        raise ScrapeException('No Piscina server configured.')

    return {
        'http': piscina_url.value,
        'https': piscina_url.value,
    }

def _twitter_populate_profile(dict_, profile):
    """
    Copy attributes from `dict_`, a `/users/lookup` API response, into a
    `Profile` instance.
    """

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


def _label_profile(db_session, profile, labels):
    """
    Add list of string labels to a profile.
    """
    print('Labelling profile', flush=True)
    profile_label_ids = [label.id for label in profile.labels]

    for id_ in labels:
        if id_ not in profile_label_ids:
            print('Label id: {}'.format(id_), flush=True)
            label = db_session.query(Label).get(id_) 

            if label:
                print('Adding label: {}'.format(label.name), flush=True)
                profile.labels.append(label)
