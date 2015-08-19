''' Helper functions for managing the search index. '''

import bleach
from markdown import markdown


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
        'private_b': profile.private,
        'post_count_i': profile.post_count,
        'site_name_s': profile.site_name(),
        'time_zone_txt_en': profile.time_zone,
        'type_s': 'Profile',
        'username_s': [u.username for u in profile.usernames],
    }

    if profile.join_date is not None:
        doc['join_date_tdt'] = profile.join_date.isoformat(),

    if profile.last_update is not None:
        last_update = profile.last_update.replace(microsecond=0).isoformat()
        doc['last_update_tdt'] = last_update,

    return doc
