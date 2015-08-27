from collections import defaultdict
from datetime import date

from dateutil.relativedelta import relativedelta
from flask import g, json, jsonify, request, send_from_directory
from flask.ext.classy import FlaskView, route
from sqlalchemy import extract, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from sqlalchemy.sql.expression import bindparam
from werkzeug.exceptions import BadRequest, Conflict, NotFound

from app.authorization import login_required
import app.database
from app.queue import scrape_queue
from app.rest import get_int_arg, get_paging_arguments, \
                     get_sort_arguments, heatmap_column, isodate, url_for
from model import Avatar, Post, Profile
from model.profile import avatar_join_profile, profile_join_self
import worker.scrape


class ProfileView(FlaskView):
    ''' Data about social media profiles. '''

    decorators = [login_required]

    def get(self, id_):
        '''
        Get the profile identified by `id`.

        **Example Response**

        .. sourcecode:: json

            {
                "avatar_url": "https://quickpin/api/file/1",
                "avatar_thumb_url": "https://quickpin/api/file/2",
                "description": "A human being.",
                "follower_count": 71,
                "friend_count": 28,
                "id": 1,
                "is_stub": false,
                "join_date": "2012-01-30T15:11:35",
                "last_update": "2015-08-18T10:51:16",
                "location": "Washington, DC",
                "name": "John Doe",
                "post_count": 1666,
                "private": false,
                "site": "twitter",
                "site_name": "Twitter",
                "time_zone": "Central Time (US & Canada)",
                "upstream_id": "11009418",
                "url": "https://quickpin/api/profile/1",
                "username": "mehaase",
                "usernames": [
                    {
                        "end_date": "2012-06-30T15:00:00",,
                        "start_date": "2012-01-01T12:00:00",,
                        "username": "mehaase"
                    },
                    ...
                ]
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token

        :>header Content-Type: application/json
        :>json str avatar_url: URL to the user's current avatar
        :>json str avatar_thumb_url: URL to a 32x32px thumbnail of the user's
            current avatar
        :>json str description: profile description
        :>json int follower_count: number of followers
        :>json int friend_count: number of friends (a.k.a. followees)
        :>json int id: unique identifier for profile
        :>json bool is_stub: indicates that this is a stub profile, e.g.
            related to another profile but has not been fully imported
        :>json str join_date: the date this profile joined its social network
            (ISO-8601)
        :>json str last_update: the last time that information about this
            profile was retrieved from the social media site (ISO-8601)
        :>json str location: geographic location provided by the user, as free
            text
        :>json str name: the full name provided by this user
        :>json int post_count: the number of posts made by this profile
        :>json bool private: true if this is a private account (i.e. not world-
            readable)
        :>json str site: machine-readable site name that this profile belongs to
        :>json str site_name: human-readable site name that this profile belongs
            to
        :>json str time_zone: the user's provided time zone as free text
        :>json str upstream_id: the user ID assigned by the social site
        :>json str url: URL endpoint for retriving more data about this profile
        :>json str username: the current username for this profile
        :>json list usernames: list of known usernames for this profile
        :>json str usernames[n].end_date: the last known date this username was
            used for this profile
        :>json str usernames[n].start_date: the first known date this username
            was used for this profile
        :>json str usernames[n].username: a username used for this profile

        :status 200: ok
        :status 400: invalid argument[s]
        :status 401: authentication required
        :status 404: user does not exist
        '''

        # Get profile.
        id_ = get_int_arg('id_', id_)
        current_avatar_id = self._current_avatar_subquery()

        profile, avatar = g.db.query(Profile, Avatar) \
                              .join(Avatar, Avatar.id == current_avatar_id) \
                              .filter(Profile.id == id_).first()

        if profile is None:
            raise NotFound("Profile '%s' does not exist." % id_)

        response = profile.as_dict()
        response['url'] = url_for('ProfileView:get', id_=profile.id)

        # Create usernames list.
        usernames = list()

        for username in profile.usernames:
            if username.end_date is not None:
                end_date = username.end_date.isoformat()
            else:
                end_date = None

            if username.start_date is not None:
                start_date = username.start_date.isoformat()
            else:
                start_date = None

            usernames.append({
                'end_date': end_date,
                'username': username.username,
                'start_date': start_date,
            })

        response['usernames'] = usernames

        # Create avatar attributes.
        response['avatar_url'] = url_for('FileView:get', id_=avatar.file.id)
        response['avatar_thumb_url'] = url_for('FileView:get',
                                               id_=avatar.thumb_file.id)

        # Send response.
        return jsonify(**response)

    @route('/<id_>/friends')
    def get_friends(self, id_):
        '''
        Return an array of profiles that are followed by the specified profile.

        **Example Response**

        .. sourcecode:: json

            {
              "friends": [
                {
                  "avatar_thumb_url": "https://quickpin/api/file/1",
                  "id": 3,
                  "url": "https://quickpin/api/profile/3",
                  "username": "rustlang"
                },
                {
                  "avatar_thumb_url": "https://quickpin/api/file/2",
                  "id": 4,
                  "url": "https://quickpin/api/profile/4",
                  "username": "ORGANICBUTCHER"
                },
                ...
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :query page: the page number to display (default: 1)
        :query rpp: the number of results per page (default: 10)

        :>header Content-Type: application/json
        :>json object friends Array of friends.
        :>json int friends[n].avatar_thumb_url a URL to a thumbnail of the
            user's current avatar
        :>json int friends[n].id Unique identifier for friend's profile.
        :>json str friends[n].url The URL to fetch this friend's profile.
        :>json str friends[n].username This friend's username.
        :>json int total_count Total count of all friends, not just those on
            the current page.

        :status 200: ok
        :status 400: invalid argument[s]
        :status 401: authentication required
        :status 404: user does not exist
        '''

        page, results_per_page = get_paging_arguments(request.args)
        current_avatar_id = self._current_avatar_subquery()

        friend_query = \
            g.db.query(Profile, Avatar) \
                .join(profile_join_self, profile_join_self.c.friend_id == Profile.id) \
                .outerjoin(Avatar, Avatar.id==current_avatar_id) \
                .filter(profile_join_self.c.follower_id == id_)

        total_count = friend_query.count()

        friend_query = \
            friend_query.order_by(Profile.is_stub, Profile.username) \
                        .limit(results_per_page) \
                        .offset((page - 1) * results_per_page)

        friends = list()

        for friend, avatar in friend_query:
            if avatar is not None:
                thumb_url = url_for(
                    'FileView:get',
                    id_=avatar.thumb_file.id
                )
            else:
                thumb_url = url_for(
                    'static',
                    filename='img/default_user_thumb.png'
                )

            friend_dict = {
                'avatar_thumb_url': thumb_url,
                'id': friend.id,
                'url': url_for('ProfileView:get', id_=friend.id),
                'username': friend.username,
            }

            friends.append(friend_dict)

        return jsonify(friends=friends, total_count=total_count)

    @route('/<id_>/followers')
    def get_followers(self, id_):
        '''
        Return an array of profiles that follow this profile.

        **Example Response**

        .. sourcecode:: json

            {
              "followers": [
                {
                  "avatar_thumb_url": "https://quickpin/api/file/1",
                  "id": 3,
                  "url": "https://quickpin/api/profile/3",
                  "username": "rustlang"
                },
                {
                  "avatar_thumb_url": "https://quickpin/api/file/2",
                  "id": 4,
                  "url": "https://quickpin/api/profile/4",
                  "username": "ORGANICBUTCHER"
                },
                ...
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :query page: the page number to display (default: 1)
        :query rpp: the number of results per page (default: 10)

        :>header Content-Type: application/json
        :>json object followers Array of followers.
        :>json int followers[n].avatar_thumb_url a URL to a thumbnail of the
            user's current avatar
        :>json int followers[n].id Unique identifier for friend's profile.
        :>json str followers[n].url The URL to fetch this friend's profile.
        :>json str followers[n].username This friend's username.
        :>json int total_count Total count of all followers, not just those on
            the current page.

        :status 200: ok
        :status 400: invalid argument[s]
        :status 401: authentication required
        :status 404: user does not exist
        '''

        page, results_per_page = get_paging_arguments(request.args)
        current_avatar_id = self._current_avatar_subquery()

        follower_query = \
            g.db.query(Profile, Avatar) \
                .join(profile_join_self,
                      profile_join_self.c.follower_id == Profile.id) \
                .outerjoin(Avatar, Avatar.id==current_avatar_id) \
                .filter(profile_join_self.c.friend_id == id_)

        total_count = follower_query.count()

        follower_query = \
            follower_query.order_by(Profile.is_stub, Profile.username) \
                          .limit(results_per_page) \
                          .offset((page - 1) * results_per_page)
        followers = list()

        for follower, avatar in follower_query:
            if avatar is not None:
                thumb_url = url_for(
                    'FileView:get',
                    id_=avatar.thumb_file.id
                )
            else:
                thumb_url = url_for(
                    'static',
                    filename='img/default_user_thumb.png'
                )

            follower_dict = {
                'avatar_thumb_url': thumb_url,
                'id': follower.id,
                'url': url_for('ProfileView:get', id_=follower.id),
                'username': follower.username,
            }

            followers.append(follower_dict)

        return jsonify(followers=followers, total_count=total_count)

    @route('/<id_>/posts')
    def get_posts(self, id_):
        '''
        Return an array of posts by this profile.

        **Example Response**

        .. sourcecode:: json

            {
              "posts": [
                {
                  "content": "If your #Tor relay is stolen or you lose control of it, please report it so we can blacklist it: https://t.co/imVnrh1FbD @TorProject",
                  "id": 4,
                  "language": "en",
                  "last_update": "2015-08-19T18:17:07",
                  "location": [
                    null,
                    null
                  ],
                  "upstream_created": "2014-11-07T16:24:05",
                  "upstream_id": "530878388605423616"
                },
                ...
              ]
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :query page: the page number to display (default: 1)
        :query rpp: the number of results per page (default: 10)

        :>header Content-Type: application/json
        :>json list posts Array of post objects.
        :>json str posts[n].content Text content of the post.
        :>json int posts[n].id Unique identifier for post.
        :>json str posts[n].language Language of post, e.g. 'en'.
        :>json str posts[n].last_update The date and time that this record was
            updated from the social media site.
        :>json str posts[n].location 2-element array of longitude and latitude.
        :>json str posts[n].upstream_created The date this was posted.
        :>json str posts[n].upstream_id The unique identifier assigned by the
        social media site.

        :status 200: ok
        :status 400: invalid argument[s]
        :status 401: authentication required
        :status 404: user does not exist
        '''

        page, results_per_page = get_paging_arguments(request.args)
        profile = g.db.query(Profile).filter(Profile.id == id_).first()

        if profile is None:
            raise NotFound('No profile exists for id={}.'.format(id_))

        posts = list()
        post_query = g.db.query(Post) \
                         .filter(Post.author_id == id_) \
                         .limit(results_per_page) \
                         .offset((page - 1) * results_per_page)


        for post in post_query:
            posts.append({
                'content': post.content,
                'id': post.id,
                'language': post.language,
                'last_update': isodate(post.last_update),
                'location': (post.longitude, post.latitude),
                'upstream_created': isodate(post.upstream_created),
                'upstream_id': post.upstream_id,
            })

        return jsonify(posts=posts)

    def index(self):
        '''
        Return an array of data about profiles.

        Note that this only returns full profiles, not "stub" profiles. If user
        A in QuickPin has a friend/follower user B but user B is not in
        QuickPin, then a "stub" profile is created for user B.

        **Example Response**

        .. sourcecode:: json

            {
                "profiles": [
                    {
                        "avatar_url": "https://quickpin/api/file/5",
                        "description": "A human being.",
                        "follower_count": 12490,
                        "friend_count": 294,
                        "id": 5,
                        "is_stub": False,
                        "join_date": "2010-01-30T18:21:35",
                        "last_update": "2015-08-18T10:51:16",
                        "location": "Washington, DC",
                        "name": "John Q. Doe",
                        "post_count": 230,
                        "private": false,
                        "site": "twitter",
                        "time_zone": "Central Time (US & Canada)",
                        "upstream_id": "123456",
                        "url": "https://quickpin/api/profile/5",
                        "username": "johndoe"
                    },
                    ...
                ],
                "total_count": 5
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :query page: the page number to display (default: 1)
        :query rpp: the number of results per page (default: 10)

        :>header Content-Type: application/json
        :>json list profiles: a list of profile objects
        :>json str profiles[n].avatar_url: a URL to the user's current avatar
            image
        :>json str profiles[n].description: profile description
        :>json int profiles[n].follower_count: number of followers
        :>json int profiles[n].friend_count: number of friends (a.k.a.
            followees)
        :>json int profiles[n].id: unique identifier for profile
        :>json bool profiles[n].is_stub: indicates that this is a stub profile,
            e.g. related to another profile but has not been fully imported (for
            this particular endpoint, is_stub will always be false)
        :>json str profiles[n].join_date: the date this profile joined its
            social network (ISO-8601)
        :>json str profiles[n].last_update: the last time that information about
            this profile was retrieved from the social media site (ISO-8601)
        :>json str profiles[n].location: geographic location provided by the
            user, as free text
        :>json str profiles[n].name: the full name provided by this user
        :>json int profiles[n].post_count: the number of posts made by this
            profile
        :>json bool profiles[n].private: true if this is a private account (i.e.
            not world-readable)
        :>json str profiles[n].site: machine-readable site name that this
            profile belongs to
        :>json str profiles[n].site_name: human-readable site name that this
            profile belongs to
        :>json str profiles[n].time_zone: the user's provided time zone as free
            text
        :>json str profiles[n].upstream_id: the user ID assigned by the social
            site
        :>json str profiles[n].url: URL endpoint for retriving more data about
            this profile
        :>json str profiles[n].username: the current username for this profile
        :>json int total_count: count of all profile objects, not just those on
            the current page

        :status 200: ok
        :status 400: invalid argument[s]
        :status 401: authentication required
        '''

        page, results_per_page = get_paging_arguments(request.args)
        current_avatar_id = self._current_avatar_subquery()

        query = g.db.query(Profile, Avatar) \
                    .outerjoin(Avatar, Avatar.id==current_avatar_id) \
                    .filter(Profile.is_stub == False)

        total_count = query.count()

        query = query.order_by(Profile.last_update.desc()) \
                     .limit(results_per_page) \
                     .offset((page - 1) * results_per_page)

        profiles = list()

        for profile, avatar in query:
            data = profile.as_dict()
            data['url'] = url_for('ProfileView:get', id_=profile.id)

            if avatar is not None:
                data['avatar_url'] = url_for(
                    'FileView:get',
                    id_=avatar.file.id
                )
            else:
                data['avatar_url'] = url_for(
                    'static',
                    filename='img/default_user_thumb.png'
                )

            profiles.append(data)

        return jsonify(
            profiles=profiles,
            total_count=total_count
        )

    def post(self):
        '''
        Request creation of new profiles.

        We don't know if a profile exists until we contact its social media
        site, and we don't want to do that on the main request thread. Instead,
        profiles are processed in the background and notifications are sent as
        profiles are discovered and scraped. Therefore, this endpoint does not
        return any new entities.

        **Example Request**

        .. sourcecode:: json

            {
                "profiles": [
                    {"username": "johndoe", "site": "instagram"},
                    {"username": "janedoe", "site": "twitter"},
                    ...
                ]
            }

        **Example Response**

        .. sourcecode:: json

            {
                "message": "21 new profiles submitted."
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :>json list profiles: a list of profiles to create
        :>json str profiles[n].username: username of profile to create
        :>json str profiles[n].site: machine-readable name of social media site

        :>header Content-Type: application/json
        :>json int id: unique identifier for new profile
        :>json str username: username of new profile
        :>json str site: machine-readable name of profile's social media site
        :>json str site_name: human-readable name of profile's social media site
        :>json str url: URL endpoint for more information about this profile

        :status 202: accepted for background processing
        :status 400: invalid request body
        :status 401: authentication required
        '''

        request_json = request.get_json()

        for profile in request_json['profiles']:
            if 'username' not in profile or profile['username'].strip() == '':
                raise BadRequest('Username is required for all profiles.')

            if 'site' not in profile or profile['site'].strip() == '':
                raise BadRequest('Site is required for all profiles.')

        for profile in request_json['profiles']:
            site = profile['site']
            username = profile['username']

            job = scrape_queue.enqueue(
                worker.scrape.scrape_account, site, username, timeout=60
            )

            job.meta['description'] = 'Scraping bio for "{}" on "{}"' \
                                      .format(username, site)
            job.meta['type'] = 'scrape'
            job.save()

        message = "{} new profiles submitted.".format(len(request_json['profiles']))
        response = jsonify(message=message)
        response.status_code = 202

        return response

    def _current_avatar_subquery(self):
        '''
        Return a scalar subquery that can be used for joining to a profile's
        current avatar.
        '''

        return g.db.query(Avatar.id) \
                   .join(avatar_join_profile,
                         avatar_join_profile.c.avatar_id == Avatar.id) \
                   .filter(avatar_join_profile.c.profile_id == Profile.id) \
                   .order_by(Avatar.end_date.desc().nullsfirst(),
                             Avatar.start_date) \
                   .limit(1) \
                   .correlate(Profile) \
                   .as_scalar()
