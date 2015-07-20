import base64
import dateutil.parser
import logging
import os
import subprocess
import sys
from textwrap import dedent

from sqlalchemy.engine import reflection
from sqlalchemy.schema import DropConstraint, DropTable, ForeignKeyConstraint, \
                              MetaData, Table

from app.config import get_path
import app.database
import cli
from model import Base, File, Post, Profile, ProfileName, User
import model.user


class DatabaseCli(cli.BaseCli):
    ''' A tool for initializing the database. '''

    def _agnostic_bootstrap(self, config):
        ''' Bootstrap the Agnostic migrations system. '''

        env = {
            'AGNOSTIC_TYPE': 'postgres',
            'AGNOSTIC_HOST': config.get('database', 'host'),
            'AGNOSTIC_USER': config.get('database', 'username'),
            'AGNOSTIC_PASSWORD': config.get('database', 'password'),
            'AGNOSTIC_SCHEMA': config.get('database', 'database'),
            'AGNOSTIC_MIGRATIONS_DIR': get_path('migrations'),
            'LANG': os.environ['LANG'], # http://click.pocoo.org/4/python3/
            'PATH': os.environ['PATH'],
        }

        process = subprocess.Popen(
            ['agnostic', 'bootstrap'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            env=env
        )
        process.wait()

        if process.returncode != 0:
            args = (process.returncode, process.stderr.read().decode('ascii'))
            self._logger.error('External process `agnostic bootstrap` failed ' \
                               'with error code (%d):\n%s' % args)
            sys.exit(1)

    def _create_fixtures(self, config):
        ''' Create fixture data. '''

        self._create_fixture_users(config)

    def _create_fixture_users(self, config):
        ''' Create user fixtures. '''

        session = app.database.get_session(self._db)
        hash_algorithm = config.get('password_hash', 'algorithm')

        try:
            hash_rounds = int(config.get('password_hash', 'rounds'))
        except:
            raise ValueError('Configuration value password_hash.rounds must' \
                             ' be an integer: %s' % rounds)

        admin = User('admin')
        admin.agency = 'QuickPin'
        admin.name = 'Administrator'
        admin.is_admin = True
        admin.password_hash = model.user.hash_password(
            'MemexPass1',
            hash_algorithm,
            hash_rounds
        )
        session.add(admin)
        session.commit()

    def _create_samples(self, config):
        ''' Create sample data. '''

        self._create_sample_profiles(config)

    def _create_sample_profiles(self, config):
        ''' Create some sample profiles. '''

        session = app.database.get_session(self._db)

        # John Doe
        johndoe_twitter = Profile(
            site='twitter',
            original_id='12345',
            name=ProfileName('john.doe', start_date='2014-04-01')
        )

        johndoe_twitter.names.append(ProfileName(
            'johnny',
            start_date='2013-06-01',
            end_date='2014-03-31'
        ))

        johndoe_twitter.names.append(ProfileName(
            'jonjon',
            start_date='2013-02-15',
            end_date='2013-05-30'
        ))

        johndoe_twitter.posts.append(Post(
            content='Going to the grocery store.',
            post_date='2015-02-04 12:34:50',
            post_date_is_exact=True,
        ))

        post = Post(
            content='Love this band!.',
            post_date='2015-03-01',
            post_date_is_exact=False,
        )

        post.attachments.append(File(
            name='helloworld.txt',
            mime='text/plain',
            content='Hello world!'.encode('utf8')
        ))

        johndoe_twitter.posts.append(post)

        johndoe_twitter.description = "I'm just a guy on the interwebs…"
        johndoe_twitter.post_count = 1205
        johndoe_twitter.friend_count = 1
        johndoe_twitter.follower_count = 3
        johndoe_twitter.join_date = dateutil.parser.parse('2013-06-01')
        johndoe_twitter.join_date_is_exact = False

        session.add(johndoe_twitter)

        # Jane Doe
        janedoe_twitter = Profile(
            site='twitter',
            original_id='23456',
            name=ProfileName('janey', start_date='2013-11-12')
        )

        janedoe_twitter.names.append(ProfileName(
            'jane',
            start_date='2013-06-14',
            end_date='2013-11-12'
        ))

        janedoe_twitter.names.append(ProfileName(
            'jane.doe',
            start_date='2013-03-15',
            end_date='2013-06-14'
        ))

        janedoe_twitter.description = "I'm just a gal on the interwebs…"
        janedoe_twitter.post_count = 1543
        janedoe_twitter.friend_count = 1
        janedoe_twitter.follower_count = 1
        johndoe_twitter.join_date = dateutil.parser.parse('2013-03-15')
        johndoe_twitter.join_date_is_exact = True
        johndoe_twitter.followers.append(janedoe_twitter)

        session.add(janedoe_twitter)

        # A couple of randos.
        johndoe_twitter.followers.append(Profile(
            site='twitter',
            original_id='345678',
            name='franky'
        ))

        johndoe_twitter.followers.append(Profile(
            site='twitter',
            original_id='456789',
            name='jenny'
        ))

        janedoe_twitter.followers.append(Profile(
            site='twitter',
            original_id='567890',
            name='joey'
        ))

        session.commit()

    def _drop_all(self):
        '''
        Drop database tables, foreign keys, etc.

        Unlike SQL Alchemy's built-in drop_all() method, this one shouldn't
        punk out if the Python schema doesn't match the actual database schema
        (a common scenario while developing).

        See: https://bitbucket.org/zzzeek/sqlalchemy/wiki/UsageRecipes/DropEverything
        '''

        tables = list()
        all_fks = list()
        metadata = MetaData()
        inspector = reflection.Inspector.from_engine(self._db)
        session = app.database.get_session(self._db)

        for table_name in inspector.get_table_names():
            fks = list()

            for fk in inspector.get_foreign_keys(table_name):
                if not fk['name']:
                    continue
                fks.append(ForeignKeyConstraint((),(),name=fk['name']))

            tables.append(Table(table_name, metadata, *fks))
            all_fks.extend(fks)

        for fk in all_fks:
            try:
                self._db.execute(DropConstraint(fk))
            except Exception as e:
                self._logger.warn('Not able to drop FK "%s".' % fk.name)
                self._logger.debug(str(e))

        for table in tables:
            try:
                self._db.execute(DropTable(table))
            except Exception as e:
                self._logger.warn('Not able to drop table "%s".' % table.name)
                self._logger.debug(str(e))

        session.commit()

    def _get_args(self, arg_parser):
        ''' Customize arguments. '''

        arg_parser.add_argument(
            'action',
            choices=('build','drop'),
            help='Specify what action to take.'
        )

        arg_parser.add_argument(
            '--debug-db',
            action='store_true',
            help='Print database queries.'
        )

        arg_parser.add_argument(
            '--sample-data',
            action='store_true',
            help='Create sample data.'
        )

    def _run(self, args, config):
        ''' Main entry point. '''

        if args.debug_db:
            # Configure database logging.
            log_level = getattr(logging, args.verbosity.upper())

            db_logger = logging.getLogger('sqlalchemy.engine')
            db_logger.setLevel(log_level)
            db_logger.addHandler(self._log_handler)

        # Connect to database.
        database_config = dict(config.items('database'))
        self._db = app.database.get_engine(database_config)

        # Run build commands.
        if args.action in ('build', 'drop'):
            self._logger.info('Dropping database tables.')
            self._drop_all()

        if args.action == 'build':
            self._logger.info('Running Agnostic\'s bootstrap.')
            self._agnostic_bootstrap(config)

            self._logger.info('Creating database tables.')
            Base.metadata.create_all(self._db)

            self._logger.info('Creating fixture data.')
            self._create_fixtures(config)

        if args.action == 'build' and args.sample_data:
            self._logger.info('Creating sample data.')
            self._create_samples(config)


_MOSS_THUMB = \
    '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' \
    'x0ejnWLsxwAAAABJRU5ErkJggg=='
