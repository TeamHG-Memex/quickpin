''' Helper functions for managing the search index. '''

import bleach
from markdown import markdown


# This index worker is commented out because it was copied from another project
# and this project does not have any search workers defined, yet.

# def make_dark_chat_doc(chat, site, room, author):
#     '''
#     Take a DarkChatMessage object (and related objects) and turn it into a Solr
#     document.
#     '''

#     body_html = markdown(chat.body)
#     body = bleach.clean(body_html, tags=[], strip=True)

#     return {
#         'chat_body_txt_en': body.strip(),
#         'chat_date_tdt': chat.message_date.replace(microsecond=0).isoformat(),
#         'chat_id_i': chat.id,
#         'id': 'DarkChatMessage:%d' % chat.id,
#         'site_id_i': site.id,
#         'site_name_txt_en': site.name,
#         'site_name_s': site.name,
#         'room_id_i': room.id,
#         'room_name_txt_en': room.name,
#         'type_s': 'DarkChatMessage',
#         'username_s': author.username,
#         'user_id_i': author.id,
#     }
