import logging
import sys

from app.database import get_engine, get_session, query_chunks
import cli
from model import Avatar, Profile
from model.profile import avatar_join_profile


class StatsCli(cli.BaseCli):
    ''' A tool for calculating (and caching) statistics. '''

    def __init__(self, *args, **kwargs):
        ''' Constructor. '''

        self.all_stats = {
            'Profile': self.profile_stats,
        }

        self._site = None
        super().__init__(*args, **kwargs)

    def profile_stats(self, session):
        current_avatar_id = (
            session
            .query(Avatar.id)
            .join(avatar_join_profile,
                  avatar_join_profile.c.avatar_id == Avatar.id)
            .filter(avatar_join_profile.c.profile_id == Profile.id)
            .order_by(Avatar.end_date.desc().nullsfirst(), Avatar.start_date)
            .limit(1)
            .correlate(Profile)
            .as_scalar()
        )

        profile_query = (
            session
            .query(Profile, Avatar)
            .outerjoin(Avatar, Avatar.id == current_avatar_id)
            .order_by(Profile.id)
        )

        total_count = session.query(Profile).count()
        progress = 0
        msg = 'Calculating stats for {} profiles.'
        self._logger.info(msg.format(total_count))

        if sys.stdout.isatty():
            pbar = self._progress_bar('Accounts', total_count)
        else:
            pbar = None

        for chunk in query_chunks(profile_query, Profile.id):
            for row in chunk:
                profile, avatar = row
                profile.current_avatar = avatar

            progress += len(chunk)
            session.commit()

            if pbar is not None:
                pbar.update(progress)

        session.commit()

        if pbar is not None:
            pbar.finish()

    def _get_args(self, arg_parser):
        ''' Customize arguments. '''

        arg_parser.add_argument(
            '--debug-db',
            action='store_true',
            help='Print database queries.'
        )

        arg_parser.add_argument(
            '--list-stats',
            action='store_true',
            help='Display names of available statistics.'
        )

        arg_parser.add_argument(
            '--site',
            help='Only compute statistics for records related to the given'
                 ' site (e.g. "twitter").'
        )

        arg_parser.add_argument(
            'stats',
            nargs='?',
            help='One or more (comma-separated) stat names to calculate. If'
                 ' not specified, then calculate all statistics.'
        )

    def _run(self, args, config):
        ''' Main entry point. '''

        self._site = args.site

        if args.debug_db:
            # Configure database logging.
            log_level = getattr(logging, args.verbosity.upper())

            db_logger = logging.getLogger('sqlalchemy.engine')
            db_logger.setLevel(log_level)
            db_logger.addHandler(self._log_handler)

        if args.list_stats:
            self._logger.info('Available stats:')

            for stat in self.all_stats.keys():
                self._logger.info(' * %s' % stat)

        else:
            database_config = dict(config.items('database'))
            db = get_engine(database_config)

            if args.stats is None:
                stats = self.all_stats.keys()
            else:
                stats = args.stats.split(',')

                for stat in stats:
                    if stat not in self.all_stats.keys():
                        msg = 'Invalid stat name: "{}"'
                        raise cli.CliError(msg.format(stat))

            for stat in stats:
                session = get_session(db)
                self.all_stats[stat](session)
