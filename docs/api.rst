********
REST API
********

.. contents::
    :depth: 2

Overview
========

QuickPin is based around a REST API. In fact, the user interface is actually
just an API client. Anything that you can do in the user interface can also be
done via API.

Representational State Transfer (REST)
======================================

We won't go into deep detail about what "RESTful" means. If you're not familiar
with the term, then you can read the dissertation which coined the term. It is
titled `Architectural Styles and the Design of Network-based Software
Architectures <http://www.ics.uci.edu/~fielding/pubs/dissertation/top.htm>`__.
It's a bit dry, but it is *the authoritative source* on REST.

For a gentler introduction, there is a good article called `How I explained REST
to My Wife <http://www.looah.com/source/view/2284>`__. There's also a `good
Stack Overflow thread <http://stackoverflow.com/questions/671118/what-exactly-
is-restful-programming>`__ on the topic.

For our purposes, we will assume that you already mostly know what REST is, but
we must emphasize a few key points:

**URLs should represent resources.**

Each URL in a RESTful API should represent a *resource*, i.e. a *noun* that the
client can manipulate. URLs should *not* represent actions. For example,
``/upload-image`` is a bad URL, because it is verb-oriented. Instead, the URL
should be noun-oriented, e.g. ``/image`` and the client should select an
appropriate verb, like ``POST /image``, to upload an image.

**The API should support content negotiation.**

This means that the client can ask for a resource in various formats, and the
server tries to provide that resource in one of the requested formats. A common
example of this is reporting: many web applications will have a report API
endpoint, for example ``/report``. If the report is available in different
formats, then the API will have an additional endpoint for each format
(``/report/pdf`` and ``/report/xls``), or it will use a query string to specify
a format (``/report?type=pdf`` and ``/report?type=xls``).

Neither of those approaches is RESTful! In a REST API, a URL is supposed to
represent a conceptual resource (e.g. a report), so having two different URLs
for the same resource is not RESTful. Instead, the client can specify what types
of response it is expecting by sending an ``Accept`` header with its request.
E.g. it can request ``/report`` and send a header like ``Accept:
application/pdf``, or ``Accept: application/vnd.ms-excel``, or even ``Accept:
application/pdf,application/vnd.ms-excel;q=0.5``. (The last example tells the
server that the client prefers PDF but can also handle XLS.)

Content negotiation allows the client and the server to figure out what
*representation* of the resource should be transferred, thus the moniker
*representational state transfer*.

**The client shouldn't need to know how to construct URLs.**

When human beings browse the web, we generally don't memorize long URL patterns
and type them in each time we want to visit a new page. Instead, we find links
on the page that look interesting and click them.

A RESTful API should be similar: the API should provide links to related
resources. For example, let's say we have an API endpoint called ``/profiles``.
This endpoint returns a list of user profiles that exist. In a non-RESTful API,
we might require the client to construct its own URLs for individual profiles.
For example, it might see a profile named ``john.doe`` and generate a URL like
``/profiles/john.doe``.

In a RESTful API, however, the response body for ``/profiles`` should include
the URL for each individual profile. So the response might look like this:

.. code:: json

    {
        "users": [
            {
                "username": john.doe,
                "profile": "https://myapp.com/profiles/john.doe"
            },
            ...
        ]
    }

With this response, the client does not need to know how to construct a profile
URL. Instead, it knows that the URL is stored in the ``profile`` field. (Note
that by convention we always include absolute URLs in our responses.) This
approach to linking resources together makes the API very resilient: the client
will continue to work even if we change our API's URL structure, because the
client is only following links given to it by the server.

The client should only know the root URL, e.g. ``/`` and all other URLs should
be links provided by the server. The only exception to this link following rule
is when constructing links that include user input, such as a URL query for a
keyword search. This exception is discussed in the JSON API section below.

.. important::

    Although we don't require that clients *know* how to construct URLs, in
    practice our Dart client must construct the majority of its URLs, because it
    also represents its user interface using URLs. For example, a user-facing
    URL like ``/dark-user/1`` might trigger an API request like ``/api/dark-
    user/1``. There's no reasonable way for our Dart client to discover URLs in
    this scenario. Nonetheless, we should still ensure that our API provides
    URLs to the client, even if the Dart client rarely needs them. It makes
    debugging faster and easier and for certain types of clients it can be a
    very natural fit.

**Use HTTP result codes correctly.**

Some APIs will return a ``200 OK`` result and a body that says "Error occurred."
That's not a good API! Given that HTTP traffic can be routed through proxies
that may do unexpected things (like caching and error reporting), it's important
that we use HTTP correctly. This means that ``200 OK`` should be reserved for
requests that are actually processed successfully.

If a request cannot be processed for any reason (e.g. the user isn't logged in),
then an appropriate HTTP code should be returned (``401 UNAUTHORIZED``). As a
rule of thumb, if the response body includes an error message, then the HTTP
code should be either ``4xx`` (client's fault) or ``5xx`` (server's fault).

JSON API
========

Our API is primarily JSON-based. We may at times support other representations,
such as providing reports in various formats or providing images in both PNG and
JPEG (using content negotiation, of course). But most request bodies will be
formatted as JSON and most response bodies be formatted as JSON (with a correct
Content-Type, of course).

Errors
======

In the event of an error, the API will return an HTTP error code (``4xx`` or
``5xx``) and will also return an error message. If the request includes the
header ``Accept: application/json``, then the error message will be
returned as a JSON object.

.. code:: json

    401 UNAUTHORIZED
    Content-Type: application/json

    {"message": "Invalid e-mail or password."}

For any other ``Accept`` header, the error will be returned as plain text
instead.

.. code:: text

    401 UNAUTHORIZED
    Content-Type: text/plain

    Invalid e-mail or password.

Quickstart
===========

Below are some common usage examples using curl. Read :ref:`endpoints` for more information.

Further Python code examples can be found in the `QuickPin API Python Client <https://github.com/TeamHG-Memex/quickpin-api.git/>`__,
which also has a simple command line utility.


**Authentication**

QuickPin authentication is easy! 

1. Obtain an API token using email/password:

.. code:: bash

    $ curl -H "Content-Type: application/json" -X POST -d '{"email":"john.doe@example.com","password":"xyz"}' http://localhost:5000/api/authentication/

    {
      "message": "Authentication is successful.",
      "token": "1|2015-12-19T13:23:03.614885.gMSIOYyeDCPLHCHTWx2F4PUASV0"
    }

2. Send authenticated requests using the token as the X-AUTH header:

.. code:: bash
    
    $ curl -H "X-AUTH:1|2015-1219T13:23:03.614885.gMSIOYyeDCPLHCHTWx2F4PUASV0" http://localhost:5000/api/profile/

    {
      "profiles": [
          {
          ...
          }
    }


**Searching for Profiles**

1. Search for profiles by upstream id. The 'upstream_id' is a Twitter or Instagram profile ID:

.. code:: bash

    $ curl -H "X-AUTH:1|2015-12-19T13:23:03.614885.gMSIOYyeDCPLHCHTWx2F4PUASV0" http://localhost:5000/api/search/?query=upstream_id:0123456789

    {
      "facets": {
      ...
      }
    ...
    }

2. Filter search results by a social site, e.g. "Twitter":

.. code:: bash

    $ curl -H "X-AUTH:1|2015-12-19T13:23:03.614885.gMSIOYyeDCPLHCHTWx2F4PUASV0" "http://localhost:5000/api/search/?query=upstream_id:0123456789&facets=site_ame_txt_en%00twitter

    {
      "facets": {
      ...
      }
    ...
    }

**Adding Profiles**

1. Add profiles by username:

.. code:: bash

    $  curl -H "Content-Type: application/json" -H "X-AUTH:1|2015-12-19T13:23:03.614885.gMSIOYyeDCPLHCHTWx2F4PUASV0" -X POST -d '{"profiles": [{"username":"hyperiongray","site":"twitter"}]}' http://localhost:5000/api/profile/

    {
      "message": "1 new profile submitted."
    }

2. Add profiles by upstream_id:

.. code:: bash

    $  curl -H "Content-Type: application/json" -H "X-AUTH:1|2015-12-19T13:23:03.614885.gMSIOYyeDCPLHCHTWx2F4PUASV0" -X POST -d '{"profiles": [{"upstream_id":"01234565789","site":"twitter"}]}' http://localhost:5000/api/profile/

    {
      "message": "1 new profile submitted."
    }

3. Add profiles as 'stubs'. 'Stub' profiles save API calls by limiting the information extracted, i.e. posts, friends, followers:

.. code:: bash

    $  curl -H "Content-Type: application/json" -H "X-AUTH:1|2015-12-19T13:23:03.614885.gMSIOYyeDCPLHCHTWx2F4PUASV0" -X POST -d '{"profiles": [{"upstream_id":"01234565789","site":"twitter", "stub" true}]}' http://localhost:5000/api/profile/

    {
      "message": "1 new profile submitted."
    }

**Editing Profiles**

Setting the score for a profile (with ID of 1) using a PUT request:

.. code:: bash

    $ curl -H "Content-Type: application/json" -H "X-AUTH: 1|2015-12-22T10:50:33.954731.CBJcKobY7UienL6GCoAt02SIiLU" -X PUT -d '{"score": 100}'  http://localhost:5000/api/profile/1

    {
      "avatar_thumb_url": "http://localhost:5000/api/file/2",
      "avatar_url": "http://localhost:5000/api/file/1",
      "description": "",
      "follower_count": 126,
    ...
    }


**Adding Profile Notes**

Add a note for a profile (with ID of 1):

.. code:: bash

    $ curl -H "Content-Type: application/json" -H "X-AUTH: 1|2015-12-22T10:50:33.954731.CBJcKobY7UienL6GCoAt02SIiLU" -X POST -d '{"notes": [{"category": "annotation", "body": "this profile is really interesting", "profile_id": 1}]}'  http://localhost:5000/api/note/

    {
      "message": "1 new notes created"
    }

Sphinx
======

The API documentation below is generated automatically from the Flask routing
table using `sphinxcontrib.httpdomain.flask <http://pythonhosted.org
/sphinxcontrib-httpdomain/>`__.

.. _endpoints:

Endpoints
=========

.. autoflask:: app:bootstrap_views()
    :undoc-static:
    :undoc-endpoints: angular, dart_package, main_dart_js
    :include-empty-docstring:
    :order: path

