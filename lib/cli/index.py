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
from model import DarkChatMessage, DarkChatRoom, DarkPrivateMessage, \
                  DarkPrivateMessageThread, DarkPost, DarkSite, DarkThread, \
                  DarkUser


class IndexCli(cli.BaseCli):
    ''' Manages the search indexes. '''

    def add_dark_chats(self, db, solr):
        ''' Add all DarkChatMessage records from `db` into the index. '''

        session = app.database.get_session(db)
        query = session.query(DarkChatMessage, DarkSite, DarkChatRoom, DarkUser) \
                       .join(DarkChatMessage.room) \
                       .join(DarkChatMessage.site) \
                       .join(DarkChatMessage.author) \
                       .order_by(DarkChatMessage.id)

        total_count = query.count()
        progress = 0
        self._logger.info("Adding %d chat messages to the index." % total_count)

        if sys.stdout.isatty():
            pbar = self._progress_bar('Chat Messages', total_count)
        else:
            pbar = None

        for chunk in app.database.query_chunks(query, DarkChatMessage.id):
            docs = list()

            for record in chunk:
                docs.append(app.index.make_dark_chat_doc(*record))

            solr.add(docs)
            solr.commit()

            if pbar is not None:
                progress += len(chunk)
                if progress > total_count:
                    break
                pbar.update(progress)

        if pbar is not None:
            pbar.finish()

    def add_dark_pms(self, db, solr):
        ''' Add all DarkPrivateMessage records from `db` into the index. '''

        session = app.database.get_session(db)
        query = session.query(DarkPrivateMessage, DarkPrivateMessageThread, DarkSite, DarkUser) \
                       .join(DarkPrivateMessage.thread) \
                       .join(DarkPrivateMessage.site) \
                       .join(DarkPrivateMessage.author) \
                       .order_by(DarkPrivateMessage.id)

        total_count = query.count()
        progress = 0
        self._logger.info("Adding %d private messages to the index." % total_count)

        if sys.stdout.isatty():
            pbar = self._progress_bar('Private Messages', total_count)
        else:
            pbar = None

        for chunk in app.database.query_chunks(query, DarkPrivateMessage.id):
            docs = list()

            for record in chunk:
                docs.append(app.index.make_dark_pm_doc(*record))

            solr.add(docs)
            solr.commit()

            if pbar is not None:
                progress += len(chunk)
                if progress > total_count:
                    break
                pbar.update(progress)

        if pbar is not None:
            pbar.finish()

    def add_dark_posts(self, db, solr):
        ''' Add all DarkPost records from `db` into the index. '''

        session = app.database.get_session(db)
        query = session.query(DarkPost, DarkSite, DarkThread, DarkUser) \
                       .join(DarkPost.thread) \
                       .join(DarkPost.site) \
                       .join(DarkPost.author) \
                       .order_by(DarkPost.id)

        total_count = query.count()
        progress = 0
        self._logger.info("Adding %d forum posts to the index." % total_count)

        if sys.stdout.isatty():
            pbar = self._progress_bar('Forum Posts', total_count)
        else:
            pbar = None

        for chunk in app.database.query_chunks(query, DarkPost.id):
            docs = list()

            for record in chunk:
                docs.append(app.index.make_dark_post_doc(*record))

            solr.add(docs)
            solr.commit()

            if pbar is not None:
                progress += len(chunk)
                if progress > total_count:
                    break
                pbar.update(progress)

        if pbar is not None:
            pbar.finish()

    def add_dark_sites(self, db, solr):
        ''' Add all DarkSite records from `db` into the index. '''

        session = app.database.get_session(db)
        query = session.query(DarkSite).order_by(DarkSite.id)

        total_count = query.count()
        progress = 0
        self._logger.info("Adding %d web sites to the index." % total_count)

        if sys.stdout.isatty():
            pbar = self._progress_bar('Web Sites', total_count)
        else:
            pbar = None

        for chunk in app.database.query_chunks(query, DarkSite.id):
            docs = list()

            for record in chunk:
                docs.append(app.index.make_dark_site_doc(record))

            solr.add(docs)
            solr.commit()

            if pbar is not None:
                progress += len(chunk)
                if progress > total_count:
                    break
                pbar.update(progress)

        if pbar is not None:
            pbar.finish()

    def add_dark_users(self, db, solr):
        ''' Add all DarkUser records from `db` into the index. '''

        session = app.database.get_session(db)
        query = session.query(DarkUser, DarkSite) \
                       .join(DarkUser.site) \
                       .order_by(DarkUser.id)

        total_count = query.count()
        progress = 0
        self._logger.info("Adding %d dark users to the index." % total_count)

        if sys.stdout.isatty():
            pbar = self._progress_bar('Users', total_count)
        else:
            pbar = None

        for chunk in app.database.query_chunks(query, DarkUser.id):
            docs = list()

            for record in chunk:
                docs.append(app.index.make_dark_user_doc(*record))

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
            'DarkChat': self.add_dark_chats,
            'DarkPrivateMessage': self.add_dark_pms,
            'DarkPost': self.add_dark_posts,
            'DarkSite': self.add_dark_sites,
            'DarkUser': self.add_dark_users,
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
                 ' delimited list of models, e.g. '
                 ' DarkChat,DarkPrivateMessage,DarkPost,DarkSite,DarkUser.'
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
