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

4. Add settings to your settings file like this::

    FREEIPA_AUTH_BACKEND_ENABLED = True
    FREEIPA_AUTH_SERVER = "ipa.foo.com"
    FREEIPA_AUTH_FAILOVER_SERVER = "ipa.failover.com"
    FREEIPA_AUTH_SSL_VERIFY = True
    FREEIPA_AUTH_UPDATE_USER_GROUPS = True
    FREEIPA_AUTH_UPDATE_USER_PERMISSIONS = True
    FREEIPA_AUTH_USER_FLAGS_BY_GROUP = {"is_staff": ["admin"], "is_superuser": ["superuser"]}
    FREEIPA_AUTH_REQUIRE_GROUP_PREFIX = "foo.django.group."
    FREEIPA_AUTH_REQUIRE_PERMISSION_PREFIX = "foo.django.permission."
    FREEIPA_AUTH_ALWAYS_UPDATE_USER = True
    FREEIPA_AUTH_AUTHORIZE_ALL_USERS = False
    FREEIPA_AUTH_USER_ATTRS_MAP = {"first_name": "givenname", "email": "mail"}

5. Start the development server and visit http://127.0.0.1:8000/admin/
   to login via freeipa rpc authentication.
