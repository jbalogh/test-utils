from django import test
from django.conf import settings
from django.core import cache, management
from django.core.handlers import wsgi
from django.db import connection, connections, DEFAULT_DB_ALIAS
from django.db.models import loading
from django.utils.encoding import smart_unicode as unicode
from django.utils.translation.trans_real import to_language

from nose.tools import eq_
from nose import SkipTest


VERSION = (0, 3)
__version__ = '.'.join(map(str, VERSION))

# We only want to run through setup_test_environment once.
IS_SETUP = False


def setup_test_environment():
    """Our own setup that hijacks Jinja template rendering."""
    global IS_SETUP
    if IS_SETUP:
        return
    IS_SETUP = True

    # Import here so it's not required to install test-utils.
    import jinja2
    old_render = jinja2.Template.render

    def instrumented_render(self, *args, **kwargs):
        context = dict(*args, **kwargs)
        test.signals.template_rendered.send(sender=self, template=self,
                                            context=context)
        return old_render(self, *args, **kwargs)

    jinja2.Template.render = instrumented_render


# We want to import this TestCase so that the template_rendered signal gets
# hooked up.
class TestCase(test.TestCase):
    """
    Subclass of ``django.test.TestCase`` that sets up Jinja template hijacking.
    """

    def __init__(self, *args, **kwargs):
        setup_test_environment()
        super(TestCase, self).__init__(*args, **kwargs)

    def setUp(self):
        cache.cache.clear()
        settings.CACHE_COUNT_TIMEOUT = None


class TransactionTestCase(test.TransactionTestCase):
    """
    Subclass of ``django.test.TransactionTestCase`` that quickly tears down
    fixtures and doesn't `flush` on setup.  This enables tests to be run in
    any order.
    """

    def _fixture_setup(self):
        """We omit the flush since it's slow and not needed since we propperly
        tear down our fixtures."""
        # If the test case has a multi_db=True flag, flush all databases.
        # Otherwise, just flush default.
        if getattr(self, 'multi_db', False):
            databases = connections
        else:
            databases = [DEFAULT_DB_ALIAS]
        for db in databases:
            if hasattr(self, 'fixtures'):
                # We have to use this slightly awkward syntax due to the fact
                # that we're using *args and **kwargs together.
                management.call_command('loaddata', *self.fixtures,
                                        **{'verbosity': 0, 'database': db})

    def _fixture_teardown(self):
        """Executes a quick truncation of MySQL tables."""
        cursor = connection.cursor()
        cursor.execute('SET FOREIGN_KEY_CHECKS=0')
        for table in connection.introspection.table_names():
            cursor.execute('TRUNCATE `%s`' % table)

        cursor.close()


class ExtraAppTestCase(TestCase):
    """
    ``TestCase`` subclass that lets you add extra apps just for testing.

    Configure extra apps through the class attribute ``extra_apps``, which is a
    sequence of 'app.module' strings. ::

        class FunTest(ExtraAppTestCase):
            extra_apps = ['fun.tests.testapp']
            ...
    """
    extra_apps = []

    @classmethod
    def setup_class(cls):
        for app in cls.extra_apps:
            settings.INSTALLED_APPS += (app,)
            loading.load_app(app)

        management.call_command('syncdb', verbosity=0, interactive=False)

    @classmethod
    def teardown_class(cls):
        # Remove the apps from extra_apps.
        for app_label in cls.extra_apps:
            app_name = app_label.split('.')[-1]
            app = loading.cache.get_app(app_name)
            del loading.cache.app_models[app_name]
            del loading.cache.app_store[app]

        apps = set(settings.INSTALLED_APPS).difference(cls.extra_apps)
        settings.INSTALLED_APPS = tuple(apps)


try:
    # You don't need a SeleniumTestCase if you don't have selenium.
    from selenium import selenium

    class SeleniumTestCase(TestCase):
        selenium = True

        def setUp(self):
            super(SeleniumTestCase, self).setUp()

            if not settings.SELENIUM_CONFIG:
                raise SkipTest()

            self.selenium = selenium(settings.SELENIUM_CONFIG['HOST'],
                                     settings.SELENIUM_CONFIG['PORT'],
                                     settings.SELENIUM_CONFIG['BROWSER'],
                                     settings.SITE_URL)
            self.selenium.start()

        def tearDown(self):
            self.selenium.close()
            self.selenium.stop()
            super(SeleniumTestCase, self).tearDown()
except ImportError:
    pass


class RequestFactory(test.Client):
    """
    Class that lets you create mock Request objects for use in testing.

    Usage::

        rf = RequestFactory()
        get_request = rf.get('/hello/')
        post_request = rf.post('/submit/', {'foo': 'bar'})

    This class re-uses the django.test.client.Client interface, docs here:
    http://www.djangoproject.com/documentation/testing/#the-test-client

    Once you have a request object you can pass it to any view function, just
    as if that view had been hooked up using a URLconf.

    http://www.djangosnippets.org/snippets/963/
    """

    def request(self, **request):
        """Return the request object as soon as it's created."""
        environ = {
            'HTTP_COOKIE':      self.cookies,
            'PATH_INFO':         '/',
            'QUERY_STRING':      '',
            'REMOTE_ADDR':       '127.0.0.1',
            'REQUEST_METHOD':    'GET',
            'SCRIPT_NAME':       '',
            'SERVER_NAME':       'testserver',
            'SERVER_PORT':       '80',
            'SERVER_PROTOCOL':   'HTTP/1.1',
            'wsgi.version':      (1, 0),
            'wsgi.url_scheme':   'http',
            'wsgi.errors':       self.errors,
            'wsgi.multiprocess': True,
            'wsgi.multithread':  False,
            'wsgi.run_once':     False,
        }
        environ.update(self.defaults)
        environ.update(request)
        return wsgi.WSGIRequest(environ)


# Comparisons

def locale_eq(a, b):
    """Compare two locales."""
    eq_(*map(to_language, [a, b]))


def trans_eq(translation, string, locale=None):
    eq_(unicode(translation), string)
    if locale:
        locale_eq(translation.locale, locale)
