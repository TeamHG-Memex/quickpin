from collections import defaultdict
from datetime import date

from dateutil.relativedelta import relativedelta
from flask import g, json, jsonify, request, send_from_directory
from flask.ext.classy import FlaskView, route
from sqlalchemy import extract, func
from sqlalchemy.sql.expression import bindparam
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import BadRequest, Conflict, NotFound

from app.authorization import login_required
import app.database
from app.queue import scrape_queue
from app.rest import get_int_arg, get_paging_arguments, get_sort_arguments, \
                     heatmap_column, url_for
from model import Profile
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
                "avatar_urls": ["https://quickpin/api/file/1", ...],
                "description": "A human being.",
                "follower_count": 71,
                "friend_count": 28,
                "id": 1,
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
        :>json str avatar_urls: a list of URLs that represent avatar images used
            by this profile
        :>json str description: profile description
        :>json int follower_count: number of followers
        :>json int friend_count: number of friends (a.k.a. followees)
        :>json int id: unique identifier for profile
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
        profile = g.db.query(Profile).filter(Profile.id == id_).first()

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

        # Create avatars list.
        avatars = list()

        for avatar in profile.avatars:
            avatars.append(url_for('FileView:get', id_=avatar.id))

        response['avatar_urls'] = avatars

        # Send response.
        return jsonify(**response)

    def index(self):
        '''
        Return an array of data about profiles.

        **Example Response**

        .. sourcecode:: json

            {
                "profiles": [
                    {
                        "avatar_urls": [
                            "https://quickpin/api/file/5"
                        ],
                        "description": "A human being.",
                        "follower_count": 12490,
                        "friend_count": 294,
                        "id": 5,
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
        :>json str profiles[n].avatar_urls: a list of URLs that represent avatar
            images used by this profile
        :>json str profiles[n].description: profile description
        :>json int profiles[n].follower_count: number of followers
        :>json int profiles[n].friend_count: number of friends (a.k.a.
            followees)
        :>json int profiles[n].id: unique identifier for profile
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

        total_count = g.db.query(Profile).count()

        query = g.db.query(Profile) \
                    .order_by(Profile.last_update.desc()) \
                    .limit(results_per_page) \
                    .offset((page - 1) * results_per_page)

        profiles = list()

        for profile in query:
            avatar_urls = list()

            for avatar in profile.avatars:
                avatar_urls.append(url_for('FileView:get', id_=avatar.id))

            data = profile.as_dict()
            data['avatar_urls'] = avatar_urls
            data['url'] = url_for('ProfileView:get', id_=profile.id)

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
