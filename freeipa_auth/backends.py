from django.contrib.auth.backends import ModelBackend
from freeipa_auth.freeipa_utils import FreeIpaSession
from django.contrib.auth.models import Permission, Group
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
                    if not self.is_authorized(user_session):
                        return
                    return self.update_user(user_session)

            except requests.ConnectionError:
                # If there was a connection error, we can try the
                # failover server once and return user
                logger.critical("Main FreeIPA server connection error")
                if tries == 1 and self.settings.FAILOVER_SERVER:
                    return self.authenticate(username, password, tries=tries+1)
                else:
                    raise

    def is_authorized(self, user_session):
        """
        If the AUTHORIZE_ALL_USERS setting is set to False
        then we check to see if freeipa user has groups
        that are user flags to authorize basic login.
        :param user_session:
        :return:
        """
        if not self.settings.AUTHORIZE_ALL_USERS:
            # If not authorize all then we check to see if
            # user has any group flags to authorize
            groups = self.get_django_user_groups(user_session)
            for group in groups:
                for flags in self.settings.USER_FLAGS_BY_GROUP.values():
                    if group in flags:
                        return True
            return False
        return True

    def get_all_user_groups(self, user_session):
        """
        We want to look for child groups as well to simplify group permission
        inheritance.
        :param user_session:
        :return:
        """
        groups = user_session.groups
        groups += user_session.user_data['memberofindirect_group']
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
        django_user_groups = self.get_django_user_groups(user_session)
        django_user_perms = self.get_django_user_perms(user_session)
        self.update_user_groups(user, django_user_groups, django_user_perms)

        user.save()
        return user

    def update_user_attrs(self, user, user_session_data):

        for attr, key in self.settings.USER_ATTRS_MAP.items():
            attr_value = user_session_data[key]
            setattr(user, attr, attr_value.pop() if isinstance(attr_value, list) else attr_value)  # noqa: E501

    def update_user_groups(self, user, group_names, perm_codenames):
        """
        Add user to django groups and give user permissions
        based on freeipa permissions, also remove user from
        any groups that do not exist.
        :param user: Django user obj
        :param group_names: List of user group names
        :param perm_codenames: List of user permission codenames
        :return:
        """

        # Set flags on user attrs
        for group, flags in self.settings.USER_FLAGS_BY_GROUP.items():
            setattr(user, group, any(flag in group_names for flag in flags))

        # Update user groups
        if self.settings.UPDATE_USER_GROUPS:
            user.groups.add(*Group.objects.filter(name__in=group_names))
            # Remove now invalid user groups if any
            user.groups.remove(*user.groups.exclude(name__in=group_names))

        # Update user permissions
        if self.settings.UPDATE_USER_PERMISSIONS_BY_GROUP:
            # Allow adding one off permissions to select users.
            perms = Permission.objects.filter(codename__in=perm_codenames)
            user.user_permissions.add(*perms)
            # Remove now invalid user permissions if any
            old_perms = user.user_permissions.exclude(codename__in=perm_codenames)  # noqa: E501
            user.user_permissions.remove(*old_perms)

    def get_django_user_groups(self, groups):
        """
        Parses and returns django specific user groups from freeipa user groups
        :return:
        """
        freeipa_user_groups_prefix = self.settings.REQUIRE_GROUP_PREFIX
        if freeipa_user_groups_prefix:
            return [group.split(freeipa_user_groups_prefix).pop()
                    for group in groups if freeipa_user_groups_prefix in group]
        return groups

    def get_django_user_perms(self, groups):
        """
        Parses and returns django specific user permissions from
        freeipa user groups.
        :return:
        """
        user_permissions_prefix = self.settings.REQUIRE_PERMISSION_PREFIX
        if user_permissions_prefix:
            return [group.split(user_permissions_prefix).pop()
                    for group in groups if user_permissions_prefix in group]
        return groups


class FreeIpaAuthSettings(object):

    defaults = {
        'BACKEND_ENABLED': True,
        'SERVER': None,
        'FAILOVER_SERVER': None,
        'SSL_VERIFY': True,
        'UPDATE_USER_GROUPS': False,
        'UPDATE_USER_PERMISSIONS_BY_GROUP': False,
        'USER_FLAGS_BY_GROUP': {},
        'USER_ATTRS_MAP': {},
        'REQUIRE_GROUP_PREFIX': None,
        'REQUIRE_PERMISSION_PREFIX': None,
        'ALWAYS_UPDATE_USER': True,
        'AUTHORIZE_ALL_USERS': False,
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
