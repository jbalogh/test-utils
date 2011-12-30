==============
Test Utilities
==============

``test_utils`` is a grab-bag of testing utilities that are pretty specific to
our Django, Jinja2, and nose setup.


settings_test
=============

test_utils allows you to create a ``settings_test`` module where you
can provide configuration settings which are used solely in your
testing environment.

For example, if I wanted to make Celery always eager in my test environment,
I could define ``CELERY_ALWAYS_EAGER`` like this:

settings.py::

    CELERY_ALWAYS_EAGER = False


settings_test.py::

    CELERY_ALWAYS_EAGER = True


API
===

.. automodule:: test_utils.runner
    :members:

.. automodule:: test_utils
    :members:
