===================
Django FreeIPA Auth
===================

Django FreeIPA Auth is a backend authentication app with a simple server failover solution
which can be included in a project's authentication backends. This app communicates with a specified
FreeIPA host server and authenticates a user to the django app upon successful freeIPA login.

Detailed documentation is in the "docs" directory.

Quick start
-----------

1. Install using pip::

    pip install django_freeipa_auth

   If running on an old version of python without security updates, include the security marker::

    pip install django_freeipa_auth[security]

2. Add "freeipa_auth" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = [
        ...
        'freeipa_auth',
    ]

3. Add "freeipa_auth.backends.FreeIpaRpcAuthBackend" to your AUTHENTICATION_BACKENDS
   in your settings file like this::

    AUTHENTICATION_BACKENDS = [
        ...
        'freeipa_auth.backends.FreeIpaRpcAuthBackend',
    ]

4. Override settings in your settings file like this::

    FREEIPA_AUTH_BACKEND_ENABLED = True
    FREEIPA_AUTH_SERVER = "ipa.foo.com" # defaults to None
    FREEIPA_AUTH_FAILOVER_SERVER = "ipa.failover.com" # defaults to None
    FREEIPA_AUTH_SSL_VERIFY = True # this would be the path to the ssl cert used
    FREEIPA_AUTH_UPDATE_USER_GROUPS = True # defaults to False
    FREEIPA_AUTH_ALWAYS_UPDATE_USER = True
    FREEIPA_AUTH_USER_ATTRS_MAP = {"first_name": "givenname", "last_name": "sn", "email": "mail"}

5. Start the development server and visit http://127.0.0.1:8000/admin/
   to login via freeipa rpc authentication.

Running Tests
-------------

Tests are run using [`tox`](https://tox.wiki/en/latest/index.html) to test on multiple `python`
and `Django` versions. To avoid needing to install multiple python binaries, use the
`docker-compose.test.yml` config to run the test in a Docker container.

````bash
docker-compose -f docker-compose.test.yml up
```
