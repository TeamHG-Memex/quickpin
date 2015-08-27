import json
import os
import sys
from urllib.parse import urljoin, urlparse, urlunparse

import requests
import scorched

import app
import app.config
import app.index
import cli
from model import Post, Profile


class IndexCli(cli.BaseCli):
    ''' Manages the search indexes. '''

    def add_posts(self, db, solr):
        ''' Add all Post records from `db` into the index. '''

        session = app.database.get_session(db)
        query = session.query(Post, Profile) \
                       .join(Post.author) \
                       .filter(Profile.is_stub == False) \
                       .order_by(Post.id)

        total_count = query.count()
        progress = 0
        self._logger.info("Adding %d posts to the index." % total_count)

        if sys.stdout.isatty():
            pbar = self._progress_bar('Posts', total_count)
        else:
            pbar = None

        for chunk in app.database.query_chunks(query, Post.id):
            docs = list()

            for post, author in chunk:
                docs.append(app.index.make_post_doc(post, author))

            solr.add(docs)
            solr.commit()

            if pbar is not None:
                progress += len(chunk)
                if progress > total_count:
                    break
                pbar.update(progress)

        if pbar is not None:
            pbar.finish()

    def add_profiles(self, db, solr):
        ''' Add all Profile records from `db` into the index. '''

        session = app.database.get_session(db)
        query = session.query(Profile) \
                       .filter(Profile.is_stub == False) \
                       .order_by(Profile.id)

        total_count = query.count()
        progress = 0
        self._logger.info("Adding %d profiles to the index." % total_count)

        if sys.stdout.isatty():
            pbar = self._progress_bar('Profiles', total_count)
        else:
            pbar = None

        for chunk in app.database.query_chunks(query, Profile.id):
            docs = list()

            for record in chunk:
                docs.append(app.index.make_profile_doc(record))

            solr.add(docs)
            solr.commit()

            if pbar is not None:
                progress += len(chunk)
                if progress > total_count:
                    break
                pbar.update(progress)

        if pbar is not None:
            pbar.finish()

    def add_models(self, db, solr, models=None):
        ''' Add all documents from `db` into the index. '''

        model_fns = {
            'Post': self.add_posts,
            'Profile': self.add_profiles,
        }

        if models is None:
            models = model_fns.keys()

        for model in models:
            try:
                model_fns[model](db, solr)
            except KeyError:
                self._logger.warn('Model not found: %s' % model)

    def delete_models(self, solr, models):
        ''' Delete specified models from Solr index. '''

        for model in models:
            self._logger.info('Deleting model "%s"' % model)
            delete_query = solr.Q(type=model)
            solr.delete_by_query(delete_query)

    def _get_args(self, arg_parser):
        ''' Customize arguments. '''

        arg_parser.add_argument(
            'action',
            choices=('add-all', 'add', 'delete-all', 'delete', 'optimize'),
            help='Specify what action to take.'
                 ' add: add specific models to the index'
                 ' add-all: add all documents to the index.'
                 ' delete: remove specific models from the index'
                 ' delete-all: remove all documents from the index.'
                 ' optimize: defrag the index.'
        )

        arg_parser.add_argument(
            'models',
            nargs='?',
            help='If adding or deleting specific models, supply a comma'
                 ' delimited list of models, e.g.  Profile,Post.'
        )

    def _run(self, args, config):
        ''' Main entry point. '''

        try:
            solr_url = config.get('solr', 'url').rstrip('/') + '/'
            solr = scorched.SolrInterface(solr_url)
        except:
            raise cli.CliError('Unable to connect to solr: %s' % solr_url)

        if args.action in ('add', 'add-all'):
            database_config = dict(config.items('database'))
            db = app.database.get_engine(database_config)

            if args.action == 'add':
                self.add_models(db, solr, args.models.split(','))
            else:
                self.add_models(db, solr)

            solr.optimize()
            self._logger.info("Added requested documents and optimized index.")

        elif args.action in ('delete', 'delete-all'):
            if args.action == 'delete':
                self.delete_models(solr, args.models.split(','))
            else:
                solr.delete_all()

            solr.optimize()
            self._logger.info("Deleted requested documents and optimized index.")

        elif args.action == 'optimize':
            solr.optimize()
            self._logger.info("Optimized index.")

        elif args.action == 'schema':
            schema_url = urljoin(solr_url, 'schema')
            self.schema(schema_url)
