==============
Test Utilities
==============

``test_utils`` is a grab-bag of testing utilities that are pretty specific to
our Django, Jinja2, and nose setup.

.. automodule:: test_utils.runner
    :members:

.. automodule:: test_utils
    :members:


Test environment
================

``test_utils`` sets an environment variable ``DJANGO_ENVIRONMENT`` and sets
it to ``'test'``.  This makes it easier to know you're in a test situation
when writing code and to do something different.

Example::

    if os.environ.get('DJANGO_ENVIRONMENT') == 'test':
        # do a test thing
    else:
        # do a non-test thing
