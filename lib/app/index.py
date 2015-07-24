''' Helper functions for managing the search index. '''

import bleach
from markdown import markdown


def make_profile_doc(profile):
    ''' Take a Profile object and turn it into a Solr document. '''

    doc = {
        'description_txt_en': profile.description,
        'follower_count_i': profile.follower_count,
        'friend_count_i': profile.friend_count,
        'profile_name_s': [n.name for n in profile.names],
        'id': 'Profile:%d' % profile.id,
        'type_s': 'Profile',
        'post_count_i': profile.post_count,
        'site_name_s': profile.site,
    }

    if profile.join_date is not None:
        doc['join_date_tdt'] = profile.join_date.isoformat(),

    return doc
