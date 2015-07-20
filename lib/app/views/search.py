from datetime import date
import re

from flask import g, jsonify, request
from flask.ext.classy import FlaskView, route
from scorched.strings import DismaxString
from werkzeug.exceptions import BadRequest

from app.authorization import login_required
from app.rest import get_paging_arguments, url_for


class SearchView(FlaskView):
    ''' API for search engine. '''

    decorators = [login_required]

    # Solr needs some special string to mark up highlighted terms. It defaults
    # to '<em>…</em>' which isn't good for our use case (see _highlight() below
    # for the explanation), so I thought it would be funny to use unicode suns
    # instead. Get it??
    HIGHLIGHT_TOKEN = '☼☼☼'

    @route('')
    def query(self):
        '''
        Run a search query.

        The response contains search hits that may be of different types, e.g.
        post hits, site hits, user hits, etc. The caller should look at the
        'type' field of each hit to determine how to handle it.

        Rather than list all of the possible return values in the documentation
        below, refer to the example that shows complete examples for every type
        of document that can be returned by this API.

        Note that all text returned by the search engine is **plain text**,
        meaning no inline markup.

        The following are highlighted:

        * Post Body
        * Post Title
        * Thread Title
        * Site Name
        * Username

        Highlighted fields are returned in this format:

        .. sourcecode:: json

            {
                highlighted: [false, true, false],
                text: ["the ", "quick", " brown fox"]
            }

        The text is returned as an array of strings. The original text can be
        constructed simply by joining this array together. A parallel array of
        booleans is also included. For each index `i`, the text in `text[i]`
        should be highlighted if and only if `highlighted[i]` is `true`. In the
        example above, the word "quick" should be highlighted by the client.

        Facets can be selected by encoding a list of facet field/value pairs as
        a list delimited by null bytes and passing it in the `facets` query
        parameter. Note that the current implementation only supports one value
        per facet field, although we intend to support multiple facets per field
        in the future. (If you do specify multiple values, then the behavior is
        undefined.)

        **Example Response**

        .. sourcecode:: json

            {
                "facets": {
                    "post_date_tdt": [
                        ["2014-03-01T00:00:00Z", 51],
                        ["2014-04-01T00:00:00Z", 1],
                        ["2014-05-01T00:00:00Z", 10],
                        ["2014-06-01T00:00:00Z", 7],
                        ["2014-08-01T00:00:00Z", 4],
                        ...
                    ],
                    "site_name_s": [
                        ["Boy Vids", 181]
                    ],
                    "username_s": [
                        ["Aneston_5*", 46],
                        ["Samuel", 30],
                        ["BaterMaster", 17],
                        ["StandByMe", 15],
                        ["arasuperup", 8],
                        ...
                    ]
                },
                "results": [
                    {
                        "post": {
                            "body": {
                                "highlighted": [false, true, false],
                                "text": ["Does anyone know ",
                                         "anything",
                                         " more about this?"]
                            },
                            "date": "2014-10-22T11:01:00Z",
                            "id": 23978,
                            "title": {
                                "highlighted": [false, true, false],
                                "text": ["Re: ", "FARM", " BOY"]
                            }
                        },
                        "site": {
                            "id": 1,
                            "name": {
                                "highlighted": [true, false],
                                "text": ["Boy", " Vids"]
                            },
                            "url": "https://quickpin/api/dark-site/1"
                        },
                        "thread": {
                            "id": 4443,
                            "title": {
                                "highlighted": [true, false],
                                "text": ["FARM", " BOY"]
                            }
                            "url": "https://quickpin/api/dark-thread/4443"
                        },
                        "type": "DarkPost",
                        "user": {
                            "id": 122,
                            "url": "https://quickpin/api/dark-user/122",
                            "username": {
                                "highlighted": [false],
                                "text": ["Jamie"]
                            },
                        }
                    },
                    {
                        "site": {
                            id": 1,
                            "name": {
                                "highlighted": [true, false],
                                "text": ["Boy", " Vids"]
                            },
                            "url": "https://quickpin/api/dark-site/1"
                        },
                        "type": "DarkSite"
                    },
                    {
                        "site": {
                            "id": 1,
                            "name": {
                                "highlighted": [true, false],
                                "text": ["Boy", " Vids"]
                            },
                            "url": "https://quickpin/api/dark-site/1"
                        },
                        "type": "DarkUser",
                        "user": {
                            "id": 226,
                            "url": "https://quickpin/api/dark-user/226",
                            "username": {
                                "highlighted": [true],
                                "text": ["Jamie"]
                            },
                        }
                    },

                ],
                "total_count": 65
            }

        :<header Content-Type: application/json
        :query facets: a null-delimited list of facet field names and values,
            delimited by null bytes (optional)
        :query page: the page number to display (default: 1)
        :query sort: a field name to sort by, optionally prefixed with a "-" to
            indicate descending sort, e.g. "post_date" sorts ascending by the
            post date, while "-username" sorts descending by username
        :query query: search query
        :query rpp: the number of results per page (default: 10)
        :query type: type of document to match, e.g. DarkPost,
            DarkSite, DarkUser, etc. (optional)

        :>header Content-Type: application/json
        :>json list results: array of search hits, each of which has a 'type'
            key that indicates what fields it will contain
        :>json int total_count: total number of documents that match the query,
            not just those included in the response

        :status 200: ok
        '''

        formatters = {
            'DarkChatMessage': self._format_dark_chat,
            'DarkPrivateMessage': self._format_dark_pm,
            'DarkPost': self._format_dark_post,
            'DarkSite': self._format_dark_site,
            'DarkUser': self._format_dark_user,
        }

        query = request.args.get('query')
        type_ = request.args.get('type')
        sort = request.args.get('sort')
        facet_args = request.args.get('facets')
        page, results_per_page = get_paging_arguments(request.args)
        start_row = (page - 1) * results_per_page

        highlight_fields = [
            'chat_body_txt_en',
            'host_s',
            'pm_body_txt_en',
            'pm_title_txt_en',
            'post_body_txt_en',
            'post_title_txt_en',
            'room_name_txt_en',
            'site_name_txt_en',
            'thread_title_txt_en',
            'username_s',
        ]

        highlight_options = {
            'snippets': 1,
            'simple.pre': SearchView.HIGHLIGHT_TOKEN,
            'simple.post': SearchView.HIGHLIGHT_TOKEN,
        }

        # These are user-friendly(er) names for the cryptic field names. Solr
        # allows a single alias to refer to multiple fields, so the fields are
        # specified as a list.
        aliases = {
            'body': ['chat_body_txt_en', 'pm_body_txt_en', 'post_body_txt_en'],
            'date': ['chat_message_date_tdt', 'pm_date_tdt', 'post_date_tdt'],
            'host': ['host_s'],
            'site': ['site_name_txt_en'],
            'title': ['pm_title_txt_en', 'post_title_txt_en', 'thread_title_txt_en'],
            'username': ['username_s'],
        }

        # Boost fields. E.g. a match to a post title ranks a result higher
        # than a match to the post body.
        boosts = {
            'username_s': 3,
            'pm_title_txt_en': 2,
            'post_title_txt_en': 2,
            'post_body_txt_en': 1,
            'chat_body_txt_en': 1,
        }

        search = g.solr.query(DismaxString(query)) \
                       .alt_parser('edismax', f=aliases, qf=boosts) \
                       .highlight(highlight_fields, **highlight_options) \
                       .paginate(start=start_row, rows=results_per_page)

        search = self._add_facets(search, facet_args)

        if type_ is not None:
            search = search.filter(type_s=type_)

        if sort is not None:
            search = search.sort_by(sort)

        response = search.execute()
        results = list()
        facets = dict()
        highlights = response.highlighting

        for doc in response:
            formatter = formatters[doc['type_s']]
            results.append(formatter(doc, highlights))

        for field, field_facets in response.facet_counts.facet_fields.items():
            facets[field] = sorted(field_facets, key=lambda f: f[0].lower())

        for field, field_facets in response.facet_counts.facet_ranges.items():
            counts = dict(field_facets['counts'])
            list_ = [(k,v) for k,v in counts.items()]
            facets[field] = sorted(list_, key=lambda f: f[0])

        return jsonify(
            results=results,
            facets=facets,
            total_count=response.result.numFound
        )

    def _add_facets(self, query, facet_args):
        ''' Add facets to a search query. '''

        # Tell Solr to generate facets on these fields.
        query = query.facet_by('site_name_s', mincount=1) \
                     .facet_by('type_s', mincount=1) \
                     .facet_by('username_s', mincount=1) \
                     .facet_range(fields='post_date_tdt',
                                  start='NOW-120MONTHS/MONTH',
                                  end='NOW/MONTH',
                                  gap='+1MONTH',
                                  mincount=1)

        # Interpret the request's facet arguments as constraints on the Solr
        # query.
        if facet_args is not None:
            facet_arg_list = facet_args.split('\x00')
            facets = {}

            try:
                for i in range(0, len(facet_arg_list), 2):
                    facets[facet_arg_list[i]] = facet_arg_list[i+1]
            except IndexError:
                raise BadRequest("Invalid facet list.")

            for field, value in facets.items():
                if field == 'post_date_tdt':
                    date_range = '[%s/MONTH TO %s+1MONTHS/MONTH]' % (value,value)
                    query = query.filter(post_date_tdt=DismaxString(date_range))
                else:
                    query = query.filter(**{field: value})

        return query

    def _format_dark_chat(self, doc, highlights):
        ''' Take a Solr doc and format it as a dark chat search hit. '''

        id_ = doc['id']
        chat_body = self._highlight(doc, highlights[id_], 'chat_body_txt_en')
        room_name = self._highlight(doc, highlights[id_], 'room_name_txt_en')

        return {
            'chat': {
                'body': chat_body,
                'date': doc['chat_date_tdt'],
                'id': doc['chat_id_i'],
            },
            'room': {
                'id': doc['room_id_i'],
                'name': room_name,
                'url': url_for('DarkChatView:get', id_=doc['room_id_i']),
            },
            'site': self._format_dark_site_fragment(doc, highlights),
            'type': doc['type_s'],
            'user': self._format_dark_user_fragment(doc, highlights),
        }

    def _format_dark_pm(self, doc, highlights):
        '''
        Take a Solr doc and format it as a dark private message search hit.
        '''

        id_ = doc['id']
        pm_body = self._highlight(doc, highlights[id_], 'pm_body_txt_en')
        pm_title = self._highlight(doc, highlights[id_], 'pm_title_txt_en')
        thread_title = self._highlight(doc, highlights[id_], 'thread_title_txt_en')

        return {
            'pm': {
                'body': pm_body,
                'date': doc['pm_date_tdt'],
                'id': doc['pm_id_i'],
                'title': pm_title,
            },
            'site': self._format_dark_site_fragment(doc, highlights),
            'thread': {
                'id': doc['thread_id_i'],
                'title': thread_title,
                'url': url_for('DarkThreadView:get', id_=doc['thread_id_i']),
            },
            'type': doc['type_s'],
            'user': self._format_dark_user_fragment(doc, highlights),
        }

    def _format_dark_post(self, doc, highlights):
        ''' Take a Solr doc and format it as a dark post search hit. '''

        id_ = doc['id']
        post_body = self._highlight(doc, highlights[id_], 'post_body_txt_en')
        post_title = self._highlight(doc, highlights[id_], 'post_title_txt_en')
        thread_title = self._highlight(doc, highlights[id_], 'thread_title_txt_en')

        return {
            'post': {
                'body': post_body,
                'date': doc['post_date_tdt'],
                'id': doc['post_id_i'],
                'title': post_title,
            },
            'site': self._format_dark_site_fragment(doc, highlights),
            'thread': {
                'id': doc['thread_id_i'],
                'title': thread_title,
                'url': url_for('DarkThreadView:get', id_=doc['thread_id_i']),
            },
            'type': doc['type_s'],
            'user': self._format_dark_user_fragment(doc, highlights),
        }

    def _format_dark_site(self, doc, highlights):
        ''' Take a Solr doc and format it as a dark site search hit. '''

        return {
            'site': self._format_dark_site_fragment(doc, highlights),
            'type': doc['type_s'],
        }

    def _format_dark_user(self, doc, highlights):
        ''' Take a Solr doc and format it as a dark user search hit. '''

        return {
            'site': self._format_dark_site_fragment(doc, highlights),
            'type': doc['type_s'],
            'user': self._format_dark_user_fragment(doc, highlights),
        }

    def _format_dark_site_fragment(self, doc, highlights):
        ''' Format the 'site' part of a search hit. '''

        id_ = doc['id']
        host_name = self._highlight(doc, highlights[id_], 'host_s')
        site_name = self._highlight(doc, highlights[id_], 'site_name_txt_en')

        return {
            'id': doc['site_id_i'],
            'host': host_name,
            'name': site_name,
            'url': url_for('DarkSiteView:get', id_=doc['site_id_i']),
        }

    def _format_dark_user_fragment(self, doc, highlights):
        ''' Format the 'user' part of a search hit. '''

        id_ = doc['id']
        username = self._highlight(doc, highlights[id_], 'username_s')

        return {
            'id': doc['user_id_i'],
            'username': username,
            'url': url_for('DarkUserView:get', id_=doc['user_id_i']),
        }

    def _highlight(self, doc, highlights, field, chars=100):
        '''
        Convert highlight data from Solr's insane format to a sane format.

        Solr tells us which parts of text to highlight by marking the text up.
        For example, by default it might give us text like "the <em>quick</em>
        brown fox", where "quick" should be highlighted. We don't want to send
        HTML to the client, because that complicates the client's task of
        displaying the data, especially clients that don't intend to render
        HTML.

        Instead, we tell Solr to mark up the highlights using a sequence of
        unicode characters that we expect to be very rare in user text (the
        HIGHLIGHT_TOKEN class member). Read the doc comment for `query(…)` for
        more details on the structure of highlighted data.

        If the field doesn't have highlighting enabled or it just didn't have
        any words that need highlighting, then the returned text is truncated to
        the first `chars` characters (approximately). This function will try to
        truncate the string on a word boundary, which affects how many
        characters are actually returned.
        '''

        if field in highlights:
            parts = list()
            highlighted = list()

            for snippet in highlights[field]:
                highlight_enabled = False

                for part in snippet.split(SearchView.HIGHLIGHT_TOKEN):
                    if part != '':
                        parts.append(part)
                        highlighted.append(highlight_enabled)

                    highlight_enabled = not highlight_enabled

            text = {'text': parts, 'highlighted': highlighted}

        elif field in doc:
            pattern = r'(.{,%d})\s?' % chars
            match = re.match(pattern, doc[field])

            if match:
                text = {'text': [match.group(1)], 'highlighted': [False]}
            else:
                # I *think* that the regex is generic enough to always
                # guarantee a match.
                raise ValueError('Unexpected solr string in doc=%s, field=%s.' %
                                 (doc['id'], doc[field]))

        else:
            text = {'text': [''], 'highlighted': [False]}

        return text
