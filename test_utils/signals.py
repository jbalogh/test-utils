import django.dispatch


# test set-up and teardown signals, allowing other apps to perform cleanup etc.
pre_setup = django.dispatch.Signal()
post_teardown = django.dispatch.Signal()
