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
from model import Profile, ProfileName
import worker.scrape


class ProfileView(FlaskView):
    ''' Data about social media profiles. '''

    decorators = [login_required]

    SORT_FIELDS = {
        'friend-count': Profile.friend_count,
        'follower-count': Profile.follower_count,
        'site': Profile.site,
        'name': ProfileName.name,
    }

    def get(self, id_):
        '''
        Get the profile identified by `id`.

        **Example Response**

        .. sourcecode:: json

            {
                "id": 208,
                "chat_activity": [5,1,0,6,10,40,30,90,19,45,101,201],
                "chat_count": 633,
                "image_activity": [0,0,0,12,22,81,56,187,38,49,168,134],
                "image_count": 747,
                "pm_activity": [16,30,30,29,59,36,100,48,79,106,72,110],
                "pm_count": 810,
                "post_activity": [144,16,30,30,29,59,36,100,48,79,106,72],
                "post_count": 975,
                "site": {
                    "id": 1,
                    "name": "Boy Vids",
                    "url": "https://avatar/api/dark-site/1"
                },
                "url": "https://avatar/api/dark-user/208",
                "username": "petar"
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token

        :>header Content-Type: application/json
        :>json int id: unique user identifier
        :>json list chat_activity: counts of chat messages per month
            for the last 12 months
        :>json int chat_count: total count of chat messages by this
            user
        :>json list image_activity: counts of images posted per month
            for the last 12 months
        :>json int image_count: total count of images posted by this
            user
        :>json list pm_activity: counts of private messages per month for the
            last 12 months
        :>json int pm_count: total count of private messages by this user
        :>json list post_activity: counts of posts per month for the
            last 12 months
        :>json int post_count: total count of posts by this user
        :>json object site: the site this username is registered on
        :>json int site.id: unique site identifier
        :>json str site.name: the name of this site
        :>json str site.url: API endpoint for data about this site
        :>json str url: API endpoint for data about this user
        :>json str username: this user's username

        :status 200: ok
        :status 400: invalid argument[s]
        :status 401: authentication required
        :status 404: user does not exist
        '''

        id_ = get_int_arg('id_', id_)
        user = g.db.query(DarkUser).filter(DarkUser.id == id_).first()

        if user is None:
            raise NotFound("User '%s' does not exist." % id_)

        return jsonify(
            id=user.id,
            chat_activity=user.chat_activity,
            chat_count=user.chat_count,
            image_activity=user.image_activity,
            image_count=user.image_count,
            pm_activity=user.pm_activity,
            pm_count=user.pm_count,
            post_activity=user.post_activity,
            post_count=user.post_count,
            site={'id': user.site.id,
                  'name': user.site.name,
                  'url': url_for('DarkSiteView:get', id_=user.site.id)},
            url=url_for('DarkSiteView:get', id_=user.id),
            username=user.username,
        )

    def index(self):
        '''
        Return an array of data about profiles.

        **Example Response**

        .. sourcecode:: json

            {
                "profiles": [
                    {
                        "description": "I'm just a guy on the interwebs…",
                        "follower_count": 3,
                        "friend_count": 1,
                        "id": 1,
                        "join_date": "2013-03-15T00:00:00",
                        "join_date_is_exact": true,
                        "last_update": null,
                        "names": [
                            {
                                "end_date": null,
                                "name": "john.doe",
                                "start_date": "2014-04-01T00:00:00"
                            },
                            {
                                "end_date": "2014-03-31T00:00:00",
                                "name": "johnny",
                                "start_date": "2013-06-01T00:00:00"
                            },
                            {
                                "end_date": "2013-05-30T00:00:00",
                                "name": "jonjon",
                                "start_date": "2013-02-15T00:00:00"
                            }
                        ],
                        "original_id": "12345",
                        "post_count": 1205,
                        "site": "twitter",
                        "site_name": "Twitter",
                        "url": "http://quickpin:5000/api/profile/1"
                    },
                ],
                "total_count": 5
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :query page: the page number to display (default: 1)
        :query rpp: the number of results per page (default: 10)

        :>header Content-Type: application/json
        :>json list profiles: a list of profile objects
        :>json str profiles[n].description: profile description
        :>json int profiles[n].follower_count: number of followers
        :>json int profiles[n].friend_count: number of friends (a.k.a.
            followees)
        :>json int profiles[n].id: unique identifier for profile
        :>json str profiles[n].join_date: the date this profile joined its
            social network (ISO-8601)
        :>json bool profiles[n].join_date_is_exact: true if the ``join_date`` is
            known with precision, false if it is just an estimate
        :>json str profiles[n].last_update: the last time that information about
            this profile was retrieved from the social media site (ISO-8601)
        :>json list profiles[n].names: a list of usernames that this profile is
            using or has used (some social sites allow users to change their
            username)
        :>json str profiles[n].names[n].end_date: the last (approximate) date
            that this name was used for this profile (null if name is still in
            use or end date is not known) (ISO-8601)
        :>json str profiles[n].names[n].name: a username used with this profile
        :>json str profiles[n].names[n].start_date: the first (approximate)
            date that this name was used for this profile (null if start date is
            not known) (ISO-8601)
        :>json str profiles[n].original_id: the user ID assigned by the social
            site
        :>json int profiles[n].post_count: the number of posts made by this
            profile
        :>json str profiles[n].site: machine-readable site name that this
            profile belongs to
        :>json str profiles[n].site_name: human-readable site name that this
            profile belongs to
        :>json str profiles[n].url: URL endpoint for retriving more data about
            this profile
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
            names = list()

            for profile_name in profile.names:
                if profile_name.end_date is not None:
                    end_date = profile_name.end_date.isoformat()
                else:
                    end_date = None

                if profile_name.start_date is not None:
                    start_date = profile_name.start_date.isoformat()
                else:
                    start_date = None

                names.append({
                    'end_date': end_date,
                    'name': profile_name.name,
                    'start_date': start_date,
                })

            avatar_urls = list()

            for avatar in profile.avatars:
                avatar_urls.append(url_for('FileView:get', id_=avatar.id))

            if profile.join_date is not None:
                join_date = profile.join_date.isoformat()
            else:
                join_date = None

            profiles.append({
                'avatar_urls': avatar_urls,
                'description': profile.description,
                'id': profile.id,
                'follower_count': profile.follower_count,
                'friend_count': profile.friend_count,
                'join_date': join_date,
                'join_date_is_exact': profile.join_date_is_exact,
                'last_update': profile.last_update,
                'names': names,
                'original_id': profile.original_id,
                'post_count': profile.post_count,
                'site': profile.site,
                'site_name': profile.site_name(),
                'url': url_for('ProfileView:get', id_=profile.id),
            })

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
                    {"name": "johndoe", "site": "instagram"},
                    {"name": "janedoe", "site": "twitter"},
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
        :>json str profiles[n].name: name of profile to create
        :>json str profiles[n].site: machine-readable name of social media site

        :>header Content-Type: application/json
        :>json int id: unique identifier for new profile
        :>json str name: name of new profile
        :>json str site: machine-readable name of profile's social media site
        :>json str site_name: human-readable name of profile's social media site
        :>json str url: URL endpoint for more information about this profile

        :status 202: accepted for background processing
        :status 400: invalid request body
        :status 401: authentication required
        '''

        request_json = request.get_json()

        for profile in request_json['profiles']:
            if 'name' not in profile or profile['name'].strip() == '':
                raise BadRequest('Name is required for all profiles.')

            if 'site' not in profile or profile['site'].strip() == '':
                raise BadRequest('Site is required for all profiles.')

        for profile in request_json['profiles']:
            site = profile['site']
            name = profile['name']

            job = scrape_queue.enqueue(
                worker.scrape.scrape_account, site, name, timeout=60
            )

            job.meta['description'] = 'Scraping bio for "{}" on "{}"'.format(name, site)
            job.meta['type'] = 'scrape'
            job.save()

        message = "{} new profiles submitted.".format(len(request_json['profiles']))
        response = jsonify(message=message)
        response.status_code = 202

        return response
