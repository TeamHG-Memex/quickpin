********
Security
********

.. contents::
    :depth: 3

Architecture
============

The application is divided into a client and a server. Ultimately, access
control decisions must be enforced by the server, because the client is under
the control of the end user. Therefore, authentication and authorization are
primarly the concern of the server.

The client does keep track of authentication and authorization state so that it
can present a consistent UI to the user: e.g. we don't want to offer an action
to the user if we know the server won't authorize the user to perform that
action. If the user hijacks the client's authenticaton and authorization data,
however, all the user can do is change the UI; the server will rightfully reject
any unauthorized requests coming from the client, regardless of the client's
internal state.

The server exposes a REST API that is carefully access controlled, since the API
provides access to a great deal of sensitive data within the application. The
server is designed to make access control easy and clear for programmers to
implement. These details are explained below.

The server also exposes static assets (stylesheets, JavaScript code, Dart code)
that are not sensitive. These assets are served without any access control.
These assets include some static images that used for the UI elements, but to be
clear, sensitive image data collected from crawls is accessible only through the
REST API and has appropriate access controls.

API Authentication
==================

.. warning::

    Authentication has not been fully implemented yet. We currently have a
    hardcoded username/password in ``lib/app/views/authenticate.py``.

Authentication is performed by email address and password. The implementation is
in ``lib/app/views/authenticate.py``. Authentication is performed by making a
REST API call with the email address and password. If authentication succeeds,
the server returns an authentication token for the client to use with future
requests. (I.e., the server does not need to send the email & username with
every single request.)

The returned token is a signed cookie that contains identifying information
about the user, such as ``1.OYNDujaJL5b8IY069FKEpARkchs``. The cryptographic
signature makes token forgery infeasible. The signature is performed with a
configurable key in ``conf/local.ini``.

To make an authenticated request, the client should place the authentication
token in the ``X-Auth`` header. Additional details on how to perform
authentication are described in the `REST API` section.

A programmer can mark an API endpoint as requiring authentication (e.g. a logged in user) by using the ``@login_required`` decorator.

.. code:: python

    @flask_app.route('/api/authentication')
    @login_required
    def whoami():
        ''' Return information about the current logged in user. '''

        return jsonify(
            id=g.user.id,
            username='admin',
            is_admin=True
        )

This example shows an API endpoint that gives the user information about his/her
own account. Obviously this API requires a logged in user, otherwise what would
the ``user`` object be set to?

The ``@login_required`` decorator should be placed *after* the route decorator
in order to indicate that the route requires an auth token. If the auth token is
not provided or if the auth token is invalid, the decorator will return an HTTP
401 error. If the authentication token exists and is valid, then the route is
allowed and the ``g.user`` object is populated with the current user object.

.. note::

    If you want to write a view that can conditionally access ``g.user``, use
    the ``@login_optional`` decorator. This decorator will attach ``g.user`` to
    the request context if the user is logged in, but it will not raise a 401
    error if the user is not logged in.

API Authorization
=================

.. warning::

    Authorization has not been fully implemented yet. We currently have a single
    ``is_admin`` boolean field on the User model in ``lib/model/user.py``.

As explained in the previous section, the client must provide an auth token for
any request which requires a logged in user. Different users may be authorized
to perform different actions. For example, an administrator user can do things
that a regular user cannot.

A programmer can mark a route as requiring an administrator by using the
``@admin_required`` decorator. It is very similar to ``@login_required`` except
that it checks if the authenticated user has administrator level access. If the
user is not authorized, the decorator returns an HTTP 403 error.

.. note::

    If you use ``@admin_required``, then you do not not need to use
    ``@login_required``.

Client Authentication & Authorization (A&A)
===========================================

As described above, the client keeps track of authentication and authorization
state in order to decide what UI elements to show to the user. For example, it
should only show the "Administration" menu item to an administrator. If this
item was shown to a non-admin user and the user clicked on it, they would see a
blank administrator interface, because they are not authorized to view or modify
administrator information.

The client implements this A&A state tracking in ``AuthenticationController`` in
``dart/lib/authentication.dart``. This controller includes two convenience
functions for accessing the A&A state: ``isLoggedIn()`` and is ``isAdmin()``.
The controller also contains a reference ``currentUser`` which contains data
about the current user, such as username.

If a component needs access to A&A state, then the authentication controller can be injected into it.

.. code:: dart

    @Component(…)
    class NavComponent {
        AuthenticationController auth;

        NavComponent(this.auth);
    }

This component takes an ``AuthenticationController`` as a constructor argument.
Angular will inject the current authentication controller instance whenever it
constructs a new NavComponent. Now the authentication controller can be used in
the NavComponent template.

.. code:: html

    <ul class='dropdown-menu' ng-show='auth.isLoggedIn()'>
      <li ng-if='auth.isAdmin()'>
        <a href='/administration'>Administration…</a>
      </li>
      <li>
        <a href='/investigations'>My Investigations…</a>
      </li>
      <li class="divider"></li>
      <li><a ng-click='auth.logOut()'>Log Out</a></li>
    </ul>

This example shows a hypothetical dropdown menu that contains menu items that
are contextually relevant to the current user. For example, the menu uses
``auth.isLoggedIn()` to only display the menu if the user is already logged in.
Then it uses ``auth.isAdmin()`` to hide the "Administration…" menu item from
non-admin users.

Common Web Flaws
================

This section covers some common web application flaws and examines how
QuickPin deals with them.

Cross Site Request Forgery (CSRF)
---------------------------------

QuickPin stores authentication information in HTML5 local storage — not in
cookies. By avoiding cookies, QuickPin side steps the issue of CSRF completely.
The auth token is only sent with requests when the client specifically inserts
it into the request headers.

Cross Site Scripting (XSS)
--------------------------

Due to the use of Angular.dart, QuickPin mostly side steps XSS concerns.
Angular.dart enforces good separation of business logic and presentation logic.
View scripts don't perform any computation; they simply bind data to a marked up
document. Angular.dart automatically escapes this data before inserting it into
the document.

Angular does allow the binding of raw HTML to a document through the
``NgBindHtml`` directive, which means we do need to be very careful about using
this directive. (The purpose of the directive is to allow user-provided content
to be inserted into a view.) ``NgBindHtml`` does allow for very carefully
controlled scrubbing of HTML content using ``NodeValidatorBuilder``, which is
our mitigation strategy if we do find a need to use this risky directive. QuickPin
already has a very simple and restrictive ``NodeValidatorBuilder`` instantiated
in main.dart that will be used by default for all ``NgBindHtml`` directives.

SQL Injection (sqli)
--------------------

QuickPin uses the `SQL Alchemy ORM <http://docs.sqlalchemy.org/>`__ to provide a
layer of abstraction between the application and the database. In typical usage,
SQL Alchemy does not use raw SQL queries. More often, it uses a query building
API that uses bound variables and automatically escapes query parameters.

**Caveats**

There are two important caveats before we simply believe, "SQL Alchemy prevents
SQL injection."

- The SQL Alchemy ``execute()`` method accepts raw SQL, which makes
  it a possible injection point. This method is rarely useful, however,
  since SQL Alchemy provides safer methods to accomplish almost any task.
  ``execute()`` should be used sparingly and only with constant query strings.
- When using a ``LIKE`` clause (a.k.a. ``.like()`` in the query builder
  API), SQL Alchemy does not automatically escape wildcards (``%`` and
  ``_``) in the user's input. If you need to sanitize a parameter for a
  like query, consider ``param.replace('%', r'\%').replace('_', r'\_')``,
  where ``param`` is the user parameter that needs to be sanitized.
