from django.contrib.auth.backends import ModelBackend
from freeipa_auth.freeipa_utils import FreeIpaSession
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
import requests
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class FreeIpaRpcAuthBackend(ModelBackend):
    """
    Free IPA RPC Authentication backend.
    Basic JSON RPC session authentication on free ipa servers
    with django user group sync.
    """

    def __init__(self):
        self.settings = FreeIpaAuthSettings()

    def authenticate(self, *args, **kwargs):
        """
        Overriden method of ModelBackend.
        Authenticate on freeipa server and sync django user groups.
        :param username:
        :param password:
        :param tries: Number of tries for authentication (internal use only)
        :return:
        """

        if self.settings.BACKEND_ENABLED:

            # get arguments from Django auth __init__
            username = kwargs.get('username', None)
            password = kwargs.get('password', None)
            tries = kwargs.get('tries', 1)

            # Grab freeipa server from settings
            server = self.settings.SERVER

            # if second try, allow for a single failover server only
            if tries == 2:
                server = self.settings.FAILOVER_SERVER

            # Specify ssl public cert for a mutual SSL handshake
            ssl_verify = self.settings.SSL_VERIFY

            # Setup FreeIPA user session
            user_session = FreeIpaSession(server, ssl_verify=ssl_verify)

            message = "Attempting to authenticate user on server: {server}"
            logger.info(message.format(server=server))

            try:
                # Authenticate and get response via RPC protocol
                response = user_session.authenticate(username, password)

                # Check response status code
                logged_in = response.status_code == 200

                # If credentials were valid then sync and return the user
                # Django will handle user sessions from here
                if logged_in:
                    return self.update_user(user_session)

            except requests.ConnectionError:
                # If there was a connection error, we can try the
                # failover server once and return user
                logger.critical("Main FreeIPA server connection error")
                if tries == 1 and self.settings.FAILOVER_SERVER:
                    return self.authenticate(username, password, tries=tries+1)
                else:
                    raise

    def get_all_user_groups(self, user_session):
        """
        We want to look for child groups as well to simplify group permission
        inheritance.
        :param user_session:
        :return:
        """
        groups = user_session.groups
        groups += user_session.user_data.get('memberofindirect_group', [])
        return list(set(groups))

    def update_user(self, user_session):
        """
        Sync freeipa user to django with user freeipa user groups groups
        :param user_session: freeipa_user_session obj
        :return:
        """

        user, created = User.objects.get_or_create(username=user_session.user)

        # Set random (secret) pass for freeipa user.
        # This user does not need to, and cannot, login
        # via classic django auth.
        user.set_password(User.objects.make_random_password(length=100))

        if not created and not self.settings.ALWAYS_UPDATE_USER:
            return user

        # Update user attrs
        self.update_user_attrs(user, user_session.user_data)

        # Sync freeipa user groups with current user
        groups = self.get_all_user_groups(user_session)
        self.update_user_groups(user, groups)

        user.save()
        return user

    def update_user_attrs(self, user, user_session_data):

        for attr, key in self.settings.USER_ATTRS_MAP.items():
            attr_value = user_session_data[key]
            setattr(user, attr, attr_value.pop() if isinstance(attr_value, list) else attr_value)  # noqa: E501

    def update_user_groups(self, user, groups):
        """
        Add user to django groups
        """
        # every user should be staff, but none should be superuser
        setattr(user, "is_staff", True)

        # Update user groups
        if self.settings.UPDATE_USER_GROUPS:
            user.groups.add(*Group.objects.filter(name__in=groups))
            # Remove now invalid user groups if any
            user.groups.remove(*user.groups.exclude(name__in=groups))


class FreeIpaAuthSettings(object):

    defaults = {
        'BACKEND_ENABLED': True,
        'SERVER': None,
        'FAILOVER_SERVER': None,
        'SSL_VERIFY': True,
        'UPDATE_USER_GROUPS': False,
        'USER_ATTRS_MAP': {'first_name': 'givenname', 'last_name': 'sn', 'email': 'mail'},
        'ALWAYS_UPDATE_USER': True,
    }

    def __init__(self, prefix='FREEIPA_AUTH_'):
        """
        Load FreeIPA Auth settings and set defaults
        if they do not exists
        """
        from django.conf import settings

        for name, default in self.defaults.items():
            value = getattr(settings, prefix + name, default)
            setattr(self, name, value)
