import os

from django.conf import settings
from django.core.management.color import no_style
from django.core.management.commands.loaddata import Command
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.backends.mysql import creation as mysql

import django_nose


def uses_mysql(connection):
    return 'mysql' in connection.settings_dict['ENGINE']


_old_handle = Command.handle
def _foreign_key_ignoring_handle(self, *fixture_labels, **options):
    """Wrap the the stock loaddata to ignore foreign key checks so we can load
    circular references from fixtures.

    This is monkeypatched into place in setup_databases().

    """
    using = options.get('database', DEFAULT_DB_ALIAS)
    commit = options.get('commit', True)
    connection = connections[using]

    if uses_mysql(connection):
        cursor = connection.cursor()
        cursor.execute('SET foreign_key_checks = 0')

    _old_handle(self, *fixture_labels, **options)

    if uses_mysql(connection):
        cursor = connection.cursor()
        cursor.execute('SET foreign_key_checks = 1')

        if commit:
            connection.close()


class SkipDatabaseCreation(mysql.DatabaseCreation):
    """Database creation class that skips both creation and flushing

    The idea is to re-use the perfectly good test DB already created by an
    earlier test run, cutting the time spent before any tests run from 5-13
    (depending on your I/O luck) down to 3.

    """
    def create_test_db(self, verbosity=1, autoclobber=False):
        # Notice that the DB supports transactions. Originally, this was done
        # in the method this overrides. The confirm method was added in Django
        # v1.3 (https://code.djangoproject.com/ticket/12991) but removed in
        # Django v1.5 (https://code.djangoproject.com/ticket/17760). In Django
        # v1.5 supports_transactions is a cached property evaluated on access.
        if callable(getattr(self.connection.features, 'confirm', None)):
            # Django v1.3-4
            self.connection.features.confirm()
        elif hasattr(self, "_rollback_works"):
            # Django v1.2 and lower
            rollback = self._rollback_works()
            self.connection.settings_dict['SUPPORTS_TRANSACTIONS'] = rollback

        return self._get_test_db_name()


class RadicalTestSuiteRunner(django_nose.NoseTestSuiteRunner):
    """This is a test runner that monkeypatches connection.creation to skip
    database creation if it appears that the DB already exists.  Your tests
    will run much faster.

    To force the normal database creation, define the environment variable
    ``FORCE_DB``.  It doesn't really matter what the value is, we just check to
    see if it's there.

    """
    def setup_databases(self):
        def should_create_database(connection):
            """Return whether we should recreate the given DB.

            This is true if the DB doesn't exist or if the FORCE_DB env var is
            truthy.

            """
            # TODO: Notice when the Model classes change and return True. Worst
            # case, we can generate sqlall and hash it, though it's a bit slow
            # (2 secs) and hits the DB for no good reason. Until we find a
            # faster way, I'm inclined to keep making people explicitly saying
            # FORCE_DB if they want a new DB.

            # Notice whether the DB exists, and create it if it doesn't:
            try:
                connection.cursor()
            except StandardError:  # TODO: Be more discerning but still DB
                                   # agnostic.
                return True
            return (os.getenv('FORCE_DB', 'false').lower()
                    not in ('false', '0', ''))

        def sql_reset_sequences(connection):
            """Return a list of SQL statements needed to reset all sequences
            for Django tables."""
            # TODO: This is MySQL-specific--see below. It should also work with
            # SQLite but not Postgres. :-(
            tables = connection.introspection.django_table_names(
                only_existing=True)
            flush_statements = connection.ops.sql_flush(
                no_style(), tables, connection.introspection.sequence_list())

            # connection.ops.sequence_reset_sql() is not implemented for MySQL,
            # and the base class just returns []. TODO: Implement it by pulling
            # the relevant bits out of sql_flush().
            return [s for s in flush_statements if s.startswith('ALTER')]
            # Being overzealous and resetting the sequences on non-empty tables
            # like django_content_type seems to be fine in MySQL: adding a row
            # afterward does find the correct sequence number rather than
            # crashing into an existing row.

        for alias in connections:
            connection = connections[alias]
            creation = connection.creation
            test_db_name = creation._get_test_db_name()

            # Mess with the DB name so other things operate on a test DB
            # rather than the real one. This is done in create_test_db when
            # we don't monkeypatch it away with SkipDatabaseCreation.
            orig_db_name = connection.settings_dict['NAME']
            connection.settings_dict['NAME'] = test_db_name

            if not should_create_database(connection):
                print ('Reusing old database "%s". Set env var FORCE_DB=1 if '
                       'you need fresh DBs.' % test_db_name)

                if getattr(settings, 'SQL_RESET_SEQUENCES', True):
                    # Reset auto-increment sequences. Apparently, SUMO's tests
                    # are horrid and coupled to certain numbers.
                    cursor = connection.cursor()
                    for statement in sql_reset_sequences(connection):
                        cursor.execute(statement)
                    connection.commit_unless_managed()  # which it is

                creation.__class__ = SkipDatabaseCreation
            else:
                # We're not using SkipDatabaseCreation, so put the DB name
                # back.
                connection.settings_dict['NAME'] = orig_db_name

        Command.handle = _foreign_key_ignoring_handle

        # With our class patch, does nothing but return some connection
        # objects:
        return super(RadicalTestSuiteRunner, self).setup_databases()

    def teardown_databases(self, old_config, **kwargs):
        """Leave those poor, reusable databases alone."""

    def setup_test_environment(self, **kwargs):
        # If we have a settings_test.py let's roll it into our settings.
        try:
            import settings_test
            # Use setattr to update Django's proxies:
            for k in dir(settings_test):
                setattr(settings, k, getattr(settings_test, k))
        except ImportError:
            pass
        super(RadicalTestSuiteRunner, self).setup_test_environment(**kwargs)


class NoDBTestSuiterunner(django_nose.NoseTestSuiteRunner):
    """A test suite runner that does not set up and tear down a database."""

    def setup_databases(self):
        """I don't want databases"""
        pass

    def teardown_databases(self, *args):
        """Let's teardown inexistant databases"""
        pass
