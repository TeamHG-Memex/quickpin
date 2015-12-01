''' Helper functions for managing the search index. '''

import bleach
from markdown import markdown

from app.rest import isodate


def make_post_doc(post, author):
    ''' Take a Post object and turn it into a Solr document. '''

    author = post.author
    site = author.site

    doc = {
        'content_txt_en': post.content,
        'id': 'Post:%d' % post.id,
        'language_s': post.language,
        'last_update_tdt': isodate(post.last_update),
        'post_date_tdt': isodate(post.upstream_created),
        'post_id_i': post.id,
        'profile_id_i': author.id,
        'site_name_txt_en': author.site_name(),
        'type_s': 'Post',
        'username_s': author.username,
    }

    if post.latitude is not None and post.longitude is not None:
        doc['location_p'] = '{},{}'.format(post.latitude, post.longitude)

    if post.location is not None:
        doc['location_txt_en'] = post.location

    return doc


def make_profile_doc(profile):
    ''' Take a Profile object and turn it into a Solr document. '''

    doc = {
        'description_txt_en': profile.description,
        'follower_count_i': profile.follower_count,
        'friend_count_i': profile.friend_count,
        'id': 'Profile:%d' % profile.id,
        'lang_s': profile.lang,
        'location_txt_en': profile.location,
        'name_txt_en': profile.name,
        'profile_id_i': profile.id,
        'private_b': profile.private,
        'post_count_i': profile.post_count,
        'site_name_txt_en': profile.site_name(),
        'type_s': 'Profile',
        'username_s': [u.username for u in profile.usernames],
        'upstream_id_s': profile.upstream_id,
    }

    if profile.join_date is not None:
        doc['join_date_tdt'] = profile.join_date.isoformat(),

    if profile.last_update is not None:
        last_update = profile.last_update.replace(microsecond=0).isoformat()
        doc['last_update_tdt'] = last_update,

    return doc
