from django.test import Client
from django .conf import settings
from django.contrib.auth.models import User
import pytest


class TestFreeIpaBackendAuth(object):

    client = Client()
    username = "dummy_freeipa_username"
    password = "dummy_freeipa_password"

    def test_login(self, settings, patch_authenticate_success):
        """Test succesful login"""

        logged_in = self.client.login(username=self.username, password=self.password)
        assert logged_in
        user = User.objects.get(username=self.username)

        # No permissions on basic login
        assert not user.is_staff
        assert not user.is_superuser

    def test_logout(self, patch_authenticate_success):
        """Test successful logout"""

        logged_in = self.client.login(username=self.username, password=self.password)
        assert logged_in
        logged_in = self.client.logout()
        assert not logged_in

    def test_update_user_groups(self, test_group, settings,
                                patch_authenticate_success, patch_remote_user_groups):
        """Test that user groups are update on first time login"""

        settings.override(FREEIPA_AUTH_UPDATE_USER_GROUPS=True)

        logged_in = self.client.login(username=self.username, password=self.password)
        assert logged_in
        user = User.objects.get(username=self.username)

        # Since the "is_staff" flag exists in the settings
        # the user will be a staff member
        assert user.is_staff

        # No mapping was provided for the superuser
        # flag so user will not be a superuser
        assert not user.is_superuser

        # The user is part of "test_group" on the freeipa server so they
        # will update in django as well
        assert test_group in user.groups.all()

    def test_update_user_groups_with_prefix(self, test_group, monkeypatch, settings,
                                            patch_authenticate_success, patch_remote_user_groups):
        """Test that user groups are mapped with a required group prefix"""

        settings.override(FREEIPA_AUTH_UPDATE_USER_GROUPS=True)

        # Patch user groups on freeipa to have the required prefix for mapping
        monkeypatch.setattr("freeipa_auth.freeipa_utils.FreeIpaSession.groups",
                            ["foo.django.group.admin",
                             "foo.django.group.test_group"])

        logged_in = self.client.login(username=self.username, password=self.password)
        assert logged_in

        # Assert that the user in the mapped django
        # groups and has the mapped permission
        user = User.objects.get(username=self.username)
        assert user.is_staff
        assert test_group in user.groups.all()

    def test_update_user_attrs(self, monkeypatch, settings,
                               patch_authenticate_success, patch_remote_user_groups):
        """Test that user attrs are updated on first time login"""

        # Mock user data from freeipa
        monkeypatch.setattr("freeipa_auth.freeipa_utils.FreeIpaSession._get_user_data",
                            lambda *args: {"givenname": ['Chester'], 'sn': ['Tester'], 'mail': ['test@enervee.com']})

        logged_in = self.client.login(username=self.username, password=self.password)
        assert logged_in

        # Assert that user attrs are mapped and saved
        user = User.objects.get(username=self.username)
        assert user.first_name == "Chester"
        assert user.last_name == "Tester"
        assert user.email == 'test@enervee.com'

    def test_always_update_user(self, settings, monkeypatch,
                                patch_authenticate_success, patch_remote_user_groups):
        """Test that user is always updated on subsequent logins if set to True in settings"""

        logged_in = self.client.login(username=self.username, password=self.password)
        assert logged_in
        user = User.objects.get(username=self.username)

        # Assert that initially user is not a superuser
        assert not user.is_superuser
        logged_in = self.client.logout()
        assert not logged_in

        # Patch user groups on freeipa to have the superuser flag
        monkeypatch.setattr("freeipa_auth.freeipa_utils.FreeIpaSession.groups",
                            ["admin", "test_group", "superuser", "test_permission"])

        # Login again
        logged_in = self.client.login(username=self.username, password=self.password)
        assert logged_in

        # User should now be superuser since
        # FREEIPA_AUTH_ALWAYS_UPDATE_USER is set to True in settings
        user = User.objects.get(username=self.username)
        assert not user.is_superuser
        assert user.is_staff

    def test_no_update_user(self, settings, monkeypatch,
                            patch_authenticate_success, patch_remote_user_groups):
        """Test that user is not updated on subsequent logins if set to False in settings"""

        settings.override(FREEIPA_AUTH_ALWAYS_UPDATE_USER=False,
                          FREEIPA_AUTH_USER_FLAGS_BY_GROUP={"is_staff": ["admin"],
                                                            'is_superuser': ['superuser']})
        # Mock user data from freeipa
        monkeypatch.setattr("freeipa_auth.freeipa_utils.FreeIpaSession._get_user_data",
                            lambda *args: {"givenname": ['Chester'], 'sn': ['Tester'], 'mail': ['test@enervee.com']})

        logged_in = self.client.login(username=self.username, password=self.password)
        assert logged_in

        user = User.objects.get(username=self.username)

        # Assert that initially user does not have last name
        assert not user.last_name
        logged_in = self.client.logout()
        assert not logged_in

        # Patch user groups on freeipa to have the superuser flag
        monkeypatch.setattr("freeipa_auth.freeipa_utils.FreeIpaSession.groups",
                            ["admin", "test_group"])

        # Login again
        logged_in = self.client.login(username=self.username, password=self.password)
        assert logged_in

        # User should still not be superuser since FREEIPA_AUTH_ALWAYS_UPDATE_USER is set to False
        user = User.objects.get(username=self.username)
        assert not user.last_name

    def test_invalid_credentials(self, patch_authenticate_fail):
        """Test that no django user is created when login credentials are invalid"""

        logged_in = self.client.login(username=self.username, password=self.password)
        assert not logged_in

        # User should not be in the database
        with pytest.raises(User.DoesNotExist):
            User.objects.get(username=self.username)

    def test_classic_django_auth(self, test_user):
        """Test that classic django auth is still the main authentication backend"""

        # Here we can see we do not need to patch the freeipa response
        # since it does not reach the freeipa backend auth when a
        # user uses the django app login credentials
        logged_in = self.client.login(username=test_user.username, password=test_user.unhashed_password)
        assert logged_in

    @pytest.mark.skip(reason="Don't want to automate remote server calls")
    def test_login_live(self, settings, liveserver_username, liveserver_password, liveserver):
        """Test succesful login on live server"""

        settings.override(FREEIPA_AUTH_SERVER=liveserver,
                          FREEIPA_AUTH_SSL_VERIFY=False)

        logged_in = self.client.login(username=liveserver_username, password=liveserver_password)

        assert logged_in
        assert User.objects.get(username=liveserver_username)

    @pytest.mark.skip(reason="Don't want to automate remote server calls")
    def test_login_live_failover(self, settings, liveserver_username, liveserver_password, liveserver):
        """
        Test authentication falls back to failover
        server if there is a connection error on main server
        """

        settings.override(FREEIPA_AUTH_SERVER="test.fake-site.com",
                          FREEIPA_AUTH_FAILOVER_SERVER=liveserver,
                          FREEIPA_AUTH_SSL_VERIFY=False)

        logged_in = self.client.login(username=liveserver_username, password=liveserver_password)

        # Client will authenticate on failover
        # server and be logged in on the django app
        assert logged_in
        assert User.objects.get(username=liveserver_username)
