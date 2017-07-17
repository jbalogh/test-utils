TEST_RUNNER = 'django_nose.runner.NoseTestSuiteRunner'

SECRET_KEY = 'Some@Secret@Key'

DATABASES = {
    'default': {
        'NAME': 'test.db',
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

INSTALLED_APPS = (
    'django_nose',
)
