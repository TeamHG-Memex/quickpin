from datetime import date
import re
from flask import g, jsonify, request
from flask.ext.classy import FlaskView, route
from scorched.strings import DismaxString
from werkzeug.exceptions import BadRequest

from app.authorization import login_required
from app.rest import get_paging_arguments


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

        * Profile Description
        * Profile Name
        * Site Name

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
                    "join_date_tdt": [
                        ["2014-03-01T00:00:00Z", 51],
                        ["2014-04-01T00:00:00Z", 1],
                        ["2014-05-01T00:00:00Z", 10],
                        ["2014-06-01T00:00:00Z", 7],
                        ["2014-08-01T00:00:00Z", 4],
                        ...
                    ],
                    "site_name_txt_en": [
                        ["twitter", 181],
                        ["instagram", 90],
                        ...
                    ],
                    "username_s": [
                        ["johndoe", 46],
                        ["janedoe", 30],
                        ["maurice.moss", 17],
                        ["jen.barber", 15],
                        ...
                    ],
                    ...
                },
                "results": [
                    {
                        "description": {
                            "highlighted": [false, true, false],
                            "text": ["My ", "unique", " description"]
                        },
                        "follower_count": 70,
                        "friend_count": 213,
                        "id": "Profile:1",
                        "post_count": 1653,
                        "site": {
                            "highlighted": [false],
                            "text": ["twitter"]
                        },
                        "username": {
                            "highlighted": [false],
                            "text": ["mehaase"]
                        }
                    },
                    ...
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
        :query type: type of document to match, e.g. Profile, Post, etc.
            (optional)

        :>header Content-Type: application/json
        :>json dict facets: dictionary of facet names and facet values/counts
        :>json list results: array of search hits, each of which has a 'type'
            key that indicates what fields it will contain
        :>json int total_count: total number of documents that match the query,
            not just those included in the response

        :status 200: ok
        '''

        formatters = {
            'Post': self._format_post,
            'Profile': self._format_profile,
        }

        query = request.args.get('query')
        type_ = request.args.get('type')
        sort = request.args.get('sort')
        facet_args = request.args.get('facets')
        page, results_per_page = get_paging_arguments(request.args)
        start_row = (page - 1) * results_per_page

        highlight_fields = [
            'content_txt_en',
            'description_txt_en',
            'location_txt_en',
            'name_txt_en',
            'site_name_txt_en',
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
            'description': ['description_txt_en'],
            'location': ['location_txt_en'],
            'name': ['name_txt_en', 'username_s'],
            'post': ['content_txt_en'],
            'site': ['site_name_txt_en'],
            'upstream_id': ['upstream_id_s'],
            'stub': ['is_stub_b'],
        }

        # Boost fields. E.g. a match to a username ranks a result higher
        # than a match to the user's description.
        boosts = {
            'name_txt_en': 3,
            'username_s': 3,
            'description_txt_en': 2,
            'location_txt_en': 2,
            'content_txt_en': 1,
            'site_name_txt_en': 1,
            'time_zone_txt_en': 1,
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
            list_ = [(k, v) for k, v in counts.items()]
            facets[field] = sorted(list_, key=lambda f: f[0])

        return jsonify(
            results=results,
            facets=facets,
            total_count=response.result.numFound
        )

    def _add_facets(self, query, facet_args):
        ''' Add facets to a search query. '''

        # Tell Solr to generate facets on these fields.
        query = query.facet_by('site_name_txt_en', mincount=1) \
                     .facet_by('username_s', mincount=1) \
                     .facet_by('type_s', mincount=1) \
                     .facet_by('is_stub_b', mincount=1) \
                     .facet_range(fields='join_date_tdt',
                                  start='NOW-120MONTHS/MONTH',
                                  end='NOW/MONTH',
                                  gap='+1MONTH',
                                  mincount=1) \
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
                if field == 'join_date_tdt':
                    date_range = '[%s/MONTH TO %s+1MONTHS/MONTH]' % (value,value)
                    query = query.filter(join_date_tdt=DismaxString(date_range))
                elif field == 'post_date_tdt':
                    date_range = '[%s/MONTH TO %s+1MONTHS/MONTH]' % (value,value)
                    query = query.filter(post_date_tdt=DismaxString(date_range))
                else:
                    query = query.filter(**{field: value})

        return query

    def _format_post(self, doc, highlights):
        ''' Take a Solr doc and format it as a post search hit. '''

        id_ = doc['id']
        content = self._highlight(doc, highlights[id_], 'content_txt_en')
        site_name = self._highlight(doc, highlights[id_], 'site_name_txt_en')
        username = self._highlight(doc, highlights[id_], 'username_s')

        formatted = {
            'content': content,
            'id': id_,
            'post_id': doc['post_id_i'],
            'posted': doc['post_date_tdt'],
            'profile_id': doc['profile_id_i'],
            'site': site_name,
            'type': doc['type_s'],
            'updated': doc['last_update_tdt'],
            'username': username,
        }

        if 'location_txt_en' in doc:
            formatted['location'] = self._highlight(doc, highlights[id_],
                                                    'location_txt_en')

        return formatted

    def _format_profile(self, doc, highlights):
        ''' Take a Solr doc and format it as a profile search hit. '''

        id_ = doc['id']
        description = self._highlight(doc, highlights[id_], 'description_txt_en')
        location = self._highlight(doc, highlights[id_], 'location_txt_en')
        name = self._highlight(doc, highlights[id_], 'name_txt_en')
        site_name = self._highlight(doc, highlights[id_], 'site_name_txt_en')
        username = self._highlight(doc, highlights[id_], 'username_s')

        formatted = {
            'description': description,
            'friend_count': doc['friend_count_i'],
            'follower_count': doc['follower_count_i'],
            'id': id_,
            'location': location,
            'name': name,
            'profile_id': doc['profile_id_i'],
            'post_count': doc['post_count_i'],
            'site': site_name,
            'type': doc['type_s'],
            'username': username,
            'upstream_id': doc['upstream_id_s'],
        }

        if 'join_date_tdt' in doc:
            formatted['joined'] = doc['join_date_tdt']

        if 'last_update_tdt' in doc:
            formatted['updated'] = doc['last_update_tdt']

        return formatted

    def _highlight(self, doc, highlights, field, chars=200):
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
