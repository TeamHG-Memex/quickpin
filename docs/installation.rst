.. _installation:

******************
Installation Guide
******************

.. contents::
    :depth: 3

Production Installation
=======================

We anticipate having a `"Dockerized" <https://www.docker.com/>`_ build to use
in production. For now, if you want to install a production instance, you
should follow the Developer Installation below.

Developer Installation
======================

These instructions will help you get a development environment up and running
on an Ubuntu 14.04 host. **We assume that you already have the QuickPin project
checked out at /opt/quickpin.**

Create QuickPin User
--------------------

For security reasons, we recommend that you run QuickPin under its own
segregated user account. Create a quickpin user as follows:

.. code:: bash

    $ sudo useradd -m quickpin

QuickPin will have read access to most of its files and directories. It will
have write access only to a very small subset of its files and directories.

Dependencies
------------

We assume that you have a way of managing conflicting dependencies, e.g. you
are using a virtual machine or venv or … something that keeps other projects
from interfering with QuickPin.

First, install these build dependencies. (We are making this a separate step so
that it's easy to automate our build process in the future.)

.. code:: bash

    $ sudo apt-get -y install curl wget python-dev unzip

Now, before we start installing the main dependencies, we need to add the Dart
package repository to APT.

.. code::

    $ sudo sh -c 'curl https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -'
    $ sudo sh -c 'curl https://storage.googleapis.com/download.dartlang.org/linux/debian/dart_stable.list > /etc/apt/sources.list.d/dart_stable.list'
    $ sudo apt-get update


We also need to ensure we have an up to date version of node.

.. code::

    $ sudo apt-get remove -y nodejs npm 
    $ curl -sL https://deb.nodesource.com/setup_4.x | sudo bash - 


Now, we can install some dependencies via APT.

.. code::

    $ sudo apt-get install -y apache2 dart libapache2-mod-wsgi-py3 \
                              build-essential tcl8.5 apt-transport-https \
                              redis-server dart postgresql postgresql-contrib \ 
                              openjdk-7-jre-headless libcurl4-gnutls-dev python3-bcrypt \
                              python3-dateutil python3-lxml python3-pip python3-psycopg2 \
                              supervisor supervisor zlib1g-dev libtiff4-dev \
                              libjpeg8-dev libfreetype6-dev liblcms1-dev libwebp-dev 


If you want to build documentation, then you'll also need Sphinx:

.. code:: bash

    $ sudo apt-get -y install graphviz python3-sphinx
    $ sudo pip3 install alabaster sphinxcontrib-httpdomain

.. tip::

  You may also wish to install the ``git`` package right now, if that's how you
  are getting source code into your environment.

**At this point, you should have the QuickPin source code stored at the path
``/opt/quickpin``.** Now install the Python dependencies.

.. code:: bash

    $ sudo pip3 install -r /opt/quickpin/install/python-dependencies.txt

.. important::

    **This project runs Python 3!** In order to avoid accidentally running
    Python 2, you may want to alias ``python`` to ``python3`` and alias ``pip``
    to ``pip3``. It is not recommended to symlink ``python`` to ``python3`` in
    case any system scripts depend on Python 2.

Our Dart code has other Dart dependencies that we need to install, using
Dart's package manager called "Pub". Set up some symlinks so that ``pub``
is in your path.

.. code:: bash

    $ sudo find /usr/lib/dart/bin/ -type f -executable \
          -exec ln -s {} /usr/local/bin/ \;
    $ sudo ln -s /usr/lib/dart /usr/lib/dart/bin/dart-sdk

.. note::

    The second instruction is there to handle a `current bug
    <http://code.google.com/p/dart/issues/detail?id=21225>`_ in one of our Dart
    libraries. It should be fixed soon when we upgrade to Angular 1.1.

By default, Pub will try to cache dependencies in ``~/.pub-cache``, but this
can be annoying if you want to install as root but run as a less privileged
user. (The dependencies would be installed in ``/root/.pub-cache`` but
QuickPin would look for them in ``/home/quickpin/.pub-cache``.) Therefore, we'll
make a system-wide Pub cache and export it through a ``PUB_CACHE``
environment variable.

.. code:: bash

    $ export PUB_CACHE=/opt/pub-cache
    $ sudo -E mkdir -p $PUB_CACHE

Note the ``-E`` argument to ``sudo`` to make sure that it can see the
``PUB_CACHE`` environment variable.

You should probably add ``PUB_CACHE`` to your ``.profile`` (or similar) so
that you don't need to remember to export this variable every time you log
in.

We also need to install the less package for node using npm,
as the ubuntu version is out of date:

.. code:: bash
        
    $ sudo npm install -g less

Now we can use Pub to bring in our dependencies.

.. code:: bash

    $ cd /opt/quickpin/static/dart
    $ sudo -E pub get
    ...snip...

Pub has some issues with weird permissions, so we also want to fix up
permissions before we continue. I created an alias for this so that I can fix permissions whenever I use pub to update dependencies.

.. code:: bash

    $ cat >> ~/.bash_aliases
    alias fixpub='sudo chown -R root:root /opt/pub-cache; sudo find /opt/pub-cache -type f -exec chmod 644 {} \; ; sudo find /opt/pub-cache -type d -exec chmod 755 {} \;'
    <Ctrl+D>
    $ . ~/.bash_aliases
    $ fixpub

You'll want to run ``fixpub`` any time you use ``pub get`` or ``pub upgrade``.

Next, you need to set up Node.js. We already installed the Node.js package
above, but we also need to symlink ``node`` to ``nodejs`` since some older
packages expect the Node.js executable to be called ``node``.

.. code:: bash

    $ sudo ln -s /usr/bin/nodejs /usr/local/bin/node


Now upgrade the Dart packages.

.. code:: bash

    $ cd /opt/quickpin/static/dart
    $ sudo -E pub upgrade
    $ fixpub


Finally, the last step is to get the Solr search engine installed. Begin by
downloading version 5.x `from here
<http://mirror.cc.columbia.edu/pub/software/apache/lucene/solr/>`__.

The archive contains an installer script, so you just need to extract that one
script and run it. You can extract the installer like this:

.. code:: bash

    $ tar xzf solr-5.2.1.tgz \
              solr-5.2.1/bin/install_solr_service.sh \
              --strip-components=2

(You'll need to adjust the ``5.2.1`` to match the version that you actually downloaded.)

After the installer is extracted, you can run it to set up Solr on your sytem —
just make sure to pass the name of the archive you download as an argument to
the installer script.

.. code:: bash

    $ sudo ./install_solr_service.sh solr-5.2.1.tgz
    id: solr: no such user
    Creating new user: solr
    Adding system user `solr' (UID 105) ...
    Adding new group `solr' (GID 113) ...
    Adding new user `solr' (UID 105) with group `solr' ...
    Creating home directory `/home/solr' ...
    Extracting solr-5.0.0.zip to /opt
    Creating /etc/init.d/solr script ...
     Adding system startup for /etc/init.d/solr ...
       /etc/rc0.d/K20solr -> ../init.d/solr
    ...

(Once again, adjust the ``5.2.1`` to match the version that you actually
downloaded.)

The installer script puts the Solr server in ``/opt/solr``, puts Solr data in
``/var/solr``, and adds a service script in ``/etc/init.d/solr`` so that you can
control Solr like any other Linux service.

.. code:: bash

    $ sudo service solr status

    Found 1 Solr nodes:

    Solr process 23399 running on port 8983
    {
      "solr_home":"/var/solr/data/",
      "version":"5.0.0 1659987 - anshumgupta - 2015-02-15 12:26:10",
      "startTime":"2015-03-24T04:37:29.172Z",
      "uptime":"0 days, 0 hours, 1 minutes, 50 seconds",
      "memory":"33.7 MB (%6.9) of 490.7 MB"}

Solr will also be configured to start automatically during bootup. You can
access a Solr admin panel by going to port ``8983`` in your browser.

.. warning::

    By default, Solr listens on ``0.0.0.0``. I'm not sure how to configure it to
    listen on the loopback interface only. This is something I will look into
    later.

To prepare Solr for use, create a new core called "quickpin".

.. code:: bash

    $ sudo -u solr /opt/solr/bin/solr create -c quickpin

    Setup new core instance directory:
    /var/solr/data/quickpin

    Creating new core 'quickpin' using command:
    http://localhost:8983/solr/admin/cores?action=CREATE&name=quickpin&instanceDir=quickpin

    {
      "responseHeader":{
        "status":0,
        "QTime":980},
      "core":"quickpin"}

That's it! Solr is installed and configured.

Permissions
-----------

QuickPin expects to have a writeable log file at ``/var/log/quickpin.log`` and
expects to be able to write to the application's ``data`` directory.

.. code:: bash

    $ sudo touch /var/log/quickpin.log
    $ sudo chown quickpin:quickpin /var/log/quickpin.log
    $ sudo chown quickpin:quickpin /opt/quickpin/data

QuickPin also minifies and combines some static resources, such as JavaScript
and CSS. It needs to store these static resources in
``/opt/quickpin/static/combined`` and
``/opt/quickpin/static/.webassets-cache``, which both need to be writable
by the user running QuickPin.

.. code:: bash

    $ sudo mkdir -p /opt/quickpin/static/combined \
                    /opt/quickpin/static/.webassets-cache
    $ sudo chown -R quickpin:quickpin \
                    /opt/quickpin/static/combined \
                    /opt/quickpin/static/.webassets-cache

Local.ini
---------

QuickPin includes a layered configuration system. First, it expects a file
called ``conf/system.ini``, and it reads configuration data from that file.
Next, it looks for a file called ``conf/local.ini``. If this file exists, then
it will be read in and any configurations it specifies will *override* the
corresponding values in ``system.ini``.

We keep ``system.ini`` version controlled and it *should not be edited* on a
per-site basis. On the other hand, ``local.ini`` is *not stored in version
control* and any site specific settings should be placed in there. We include a
``local.ini.template`` just for this purpose.

.. code:: bash

    $ sudo cp /opt/quickpin/conf/local.ini.template \
              /opt/quickpin/conf/local.ini

You should edit local.ini and provide values for the following keys:

- `username`: The application username. We recommend the name 'quickpin'.
- `password`: Generate a secure password for the application user.
- `super_username`: The user used for database administration. We recommend the
  name 'quickpin_su'.
- `super_password`: Generate a secure password for the super user.
- `SECRET_KEY`: A cryptographic key that Flask uses to sign authentication
  tokens. Set this to a long, random string, for example by running ``openssl
  rand -base64 30``.

Whatever values you pick, keep them handy: you'll need them in the next section.
You can also configure non-standard setups by overriding other values from
system.ini in the local.ini.

Database (PostgreSQL)
---------------------

If you followed the steps above, you've already installed PostgreSQL. Now we
need to add some credentials for QuickPin to use when accessing PostgresSQL.

You should set ``super_password`` below to the same password that you put in the
``super_password`` field in local.ini. You should set ``regular_password`` to
the ``password`` field in local.ini.

.. code:: bash

    $ sudo -u postgres createdb quickpin
    $ sudo -u postgres psql quickpin
    psql (9.3.6)
    Type "help" for help.

    quickpin=# DROP EXTENSION plpgsql;
    DROP EXTENSION
    quickpin=# CREATE USER quickpin_su PASSWORD 'super_password';
    CREATE ROLE
    quickpin=# ALTER DATABASE quickpin OWNER TO quickpin_su;
    ALTER DATABASE
    quickpin=# CREATE USER quickpin PASSWORD 'regular_password';
    CREATE ROLE
    quickpin=# ALTER DEFAULT PRIVILEGES FOR USER quickpin_su GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO quickpin;
    ALTER DEFAULT PRIVILEGES
    quickpin=# ALTER DEFAULT PRIVILEGES FOR USER quickpin_su GRANT USAGE ON SEQUENCES TO quickpin;
    ALTER DEFAULT PRIVILEGES
    quickpin=# \q

.. note::

    If you're looking for a graphical Postgres client, `pgAdmin
    <http://www.pgadmin.org/>`__ is cross platform, open source, and quite good.

Finally, QuickPin needs to initialize its database tables and load some data
fixtures.

.. code:: bash

    $ sudo -u quickpin python3 /opt/quickpin/bin/database.py build
    2015-03-21 06:03:43 [cli] INFO: Dropping existing database tables.
    2015-03-21 06:03:43 [cli] INFO: Running Agnostic's bootstrap.
    2015-03-21 06:03:43 [cli] INFO: Creating database tables.
    2015-03-21 06:03:43 [cli] INFO: Creating fixture data.

You can re-run this command at any point in order to clear out the database and
start from scratch. You can also pass a ``--sample-data`` flag to get some
sample data included in the database build.

.. note::

    By default, Postgres is only accessible on a local Unix socket. If you want
    to be able to access Postgres remotely for development purposes, add a line
    to the /etc/postgres/.../pg_hba.conf file like this:

    host all all 192.168.31.0/24 trust

    This line allows TCP connections from the specified subnet. Restart Postgres
    after changing this configuration value.

Supervisord
-----------

Most of the daemons we use have ``init`` scripts and launch automatically when
the system boots, but some of them do not. For this latter category, we use
``supervisord`` to make sure these processes start, and in the event that a
process unexpectedly fails, ``supervisord`` will automatically restart it.

.. code:: bash

    $ sudo cp /opt/quickpin/install/supervisor.conf \
              /etc/supervisor/conf.d/quickpin.conf
    $ sudo killall -HUP supervisord

Development Server
------------------

You should now be able to run a development server. We are using the `Flask
microframework <http://flask.pocoo.org/>`_, which has a handy dev server
built in.

.. code:: bash

    $ cd /opt/quickpin/bin/
    $ sudo -u quickpin python3 run-server.py --debug
     * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
     * Restarting with inotify reloader

.. warning::

    Note that the server runs on the loopback interface by default. The Flask
    dev server allows arbitrary code execution, which makes it extremely
    dangerous to run the dev server on a public IP address!

If you wish to expose the dev server to a network interface, you can bind
it to a different IP address, e.g.:

.. code:: bash

    $ sudo -u quickpin python3 run-server.py --ip 0.0.0.0 --debug
     * Running on http://0.0.0.0:5000/ (Press CTRL+C to quit)
     * Restarting with inotify reloader

Most of the time, you will want to enable the dev server's debug mode. This
mode has the following features:

- Automatically reloads when your Python source code changes. (It is oblivious
  to changes in configuration files, Dart source, Less source, etc.)
- Disables HTTP caching of static assets.
- Disables logging to /var/log/quickpin.log. Log messages are still displayed
  on the console.
- Uses Dart source instead of the Dart build product. (More on this later.)

You'll use the dev server in debug mode for 90% of your development.

Dartium
-------

If you are running the dev server in debug mode, then it will run the
application from Dart source code. This means you need a browser that has
a Dart VM! This browser is called *Dartium* and it's basically the same
as Chromium except with Dart support. It has the same basic features,
web kit inspector, etc.

*You should use Dartium while you develop.* Download Dartium from the `Dart
downloads page <https://www.dartlang.org/tools/download.html>`_. Make sure
to download Dartium by itself, not the whole SDK. (You already installed
the SDK if you followed the instructions above.)

You can unzip the Dartium archive anywhere you want. I chose to put it in
``/opt/dartium``. In order to run Dartium, you can either run it in place, e.g.
``/opt/dartium/chrome`` or for convenience, you might want to add a symlink:

.. code:: bash

    $ ln -s /opt/dartium/chrome /usr/local/bin

Now you can run Dart from any directory by typing ``dartium``.

.. note::

    At this point, you should be able to run QuickPin by running the dev server in
    debug mode and using Dartium to access it.

Dart Build
----------

If you run the dev server without ``--debug``, it will use the
Dart build product instead of the source code. Therefore, you need to run
a Dart build if you are going to run a server without debug mode. This same
process is used when deploying QuickPin to production.

Don't forget that you should have ``$PUB_CACHE`` defined before running this
build, and note the use of ``sudo -E``.

.. code:: bash

    $ cd /opt/quickpin/static/dart
    $ sudo -E pub build

Now you can run your dev server in non-debug mode and use QuickPin with a
standard web brower such as Chrome. If you encounter any errors in this mode,
you'll find that they are nearly impossible to debug because of the conversion
from Dart to JavaScript and the subsequent tree shaking and minification.
Add ``--mode=debug`` to your ``pub build`` command to generate more readable
JavaScript errors.

Apache Server
-------------

At some point, you'll want to test against real Apache, not just the dev
server. There are some Apache configuration files in the ``/install``
directory for this purpose.

.. code:: bash

    $ sudo cp /opt/quickpin/install/apache.conf \
              /etc/apache2/sites-available/quickpin.conf
    $ sudo cp /opt/quickpin/install/server.*  /etc/apache2/
    $ sudo a2ensite quickpin
    $ sudo a2enmod headers rewrite ssl
    $ sudo a2dissite 000-default default-ssl
    Site 000-default disabled.
    Site default-ssl already disabled
    To activate the new configuration, you need to run:
      service apache2 reload
    $ sudo service apache2 reload
     * Reloading web server apache2

The Apache configuration will always use the Dart build product and it will not
automatically reload when Python sources change, so it's really
only useful for final testing. It is very cumbersome to use Apache for active
development.

The Apache server uses a self-signed TLS certificate by default, which means
that you will get TLS verification errors and an ugly red X.  You can
`generate your own certificate
<http://www.akadia.com/services/ssh_test_certificate.html>`_
and set it to trusted in order to avoid the TLS warnings. QuickPin doesn't
use http/80 (except to redirect to port 443) and it uses
`HSTS <http://en.wikipedia.org/wiki/HTTP_Strict_Transport_Security>`_
to encourage user agents to only make requests over https/443.

At this point, you should be able to access QuickPin in a normal browser on port
443!

When you upgrade QuickPin, you can tell Apache to refresh by touching the
``/opt/quickpin/application.wsgi`` file.
