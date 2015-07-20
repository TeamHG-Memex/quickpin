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
from app.rest import get_int_arg, get_paging_arguments, get_sort_arguments, \
                     heatmap_column, url_for
from model import Profile, ProfileName


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
                "max_images": 187,
                "max_pms": 106,
                "max_posts": 144,
                "total_count": 3758,
                "users": [
                    {
                        "id": 208,
                        "chat_activity": [5,1,0,6,10,40,30,90,19,45,101,201],
                        "chat_count": 633,
                        "image_activity": [0,0,0,12,22,81,56,187,38,49,168,134],
                        "image_count": 747,
                        "pm_activity": [16,30,30,29,59,36,100,48,79,106,72,100],
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
                    },
                    ...
                ]
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :query page: the page number to display (default: 1)
        :query rpp: the number of results per page (default: 10)
        :query site_id: only list users belonging to this site
        :query sort: field name to sort by: "images", "pms", "posts", "site", or
            "username". defaults to ascending sort, but a '-' prefix indicates
            descending sort. (default: "-posts")

        :>header Content-Type: application/json
        :>json int max_images: the maximum image_activity value across all users
            (useful as a scale for Y axis)
        :>json int max_pms: the maximum pm_activity value across all users
            (useful as a scale for Y axis)
        :>json int max_posts: the maximum post_activity value across all users
            (useful as a scale for Y axis)
        :>json int total_count: the total number of all users (not just the ones
            on the current page)
        :>json list users: a list of user objects
        :>json int users[n].id: unique user identifier
        :>json list users[n].chat_activity: counts of chat messages per month
            for the last 12 months
        :>json int users[n].chat_count: total count of chat messages by this
            user
        :>json list users[n].image_activity: counts of images posted per month
            for the last 12 months
        :>json int users[n].image_count: total count of images posted by this
            user
        :>json list users[n].pm_activity: counts of private messages per month
            for the last 12 months
        :>json int users[n].pm_count: total count of private messages by this
            user
        :>json list users[n].post_activity: counts of posts per month for the
            last 12 months
        :>json int users[n].post_count: total count of posts by this user
        :>json str post_url: API endpoint for this user's posts
        :>json object users[n].site: the site this username is registered on
        :>json int users[n].site.id: unique site identifier
        :>json str users[n].site.name: the name of this site
        :>json str users[n].site.url: API endpoint for data about this site
        :>json str users[n].url: API endpoint for data about this user
        :>json str users[n].username: this user's username

        :status 200: ok
        :status 400: invalid argument[s]
        :status 401: authentication required
        '''

        page, results_per_page = get_paging_arguments(request.args)
        sort = get_sort_arguments(request.args, '-follower-count', ProfileView.SORT_FIELDS)

        total_count = g.db.query(Profile).count()

        query = g.db.query(Profile) \
                    .join(Profile.names) \
                    .order_by(*sort) \
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

            if profile.join_date is not None:
                join_date = profile.join_date.isoformat()
            else:
                join_date = None

            profiles.append({
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
