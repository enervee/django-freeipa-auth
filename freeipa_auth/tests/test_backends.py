import pytest
import requests

from unittest import mock
from django.test import override_settings
from django.contrib.auth import backends

from freeipa_auth.backends import FreeIpaRpcAuthBackend, FreeIpaAuthSettings


class TestFreeIpaRpcAuthBackend:
    username = "dummy_freeipa_username"
    password = "dummy_freeipa_password"

    def test_init(self, settings):
        backend = FreeIpaRpcAuthBackend()
        assert backend is not None
    
    @override_settings(
        FREEIPA_AUTH_SERVER="ipa.foo.com",
        FREEIPA_AUTH_FAILOVER_SERVER="ipa.failover.com",
        FREEIPA_AUTH_SSL_VERIFY="/path/to/ssl", 
    )
    @mock.patch('freeipa_auth.backends.FreeIpaSession')
    def test_authenicate_failover_server(self, mock_freeipa):
        """
        Asserts that if this is the second attempt, we use
        the failover server.
        """
        mock_response = mock.MagicMock()
        mock_response.status_code = 418
        mock_freeipa.return_value.authenticate = mock.Mock(return_value=mock_response)
        backend = FreeIpaRpcAuthBackend()
        backend.authenticate(
            username=self.username,
            password=self.password,
            tries=2,
        )
        mock_freeipa.assert_called_once_with(
            "ipa.failover.com",
            ssl_verify="/path/to/ssl"
        )

    @override_settings(
        FREEIPA_AUTH_SERVER="ipa.foo.com",
        FREEIPA_AUTH_FAILOVER_SERVER="ipa.failover.com",
        FREEIPA_AUTH_SSL_VERIFY="/path/to/ssl", 
    )
    @mock.patch('freeipa_auth.backends.logger.critical') # mute for tests
    @mock.patch('freeipa_auth.backends.FreeIpaSession')
    def test_recursive_call_with_failover_server(self, mock_freeipa, mock_logger_critical):
        """
        Asserts that when we're on the first try and we
        have a failover server set, a second attempt is made
        if we have an error raised on the first try.
        """
        mock_freeipa.return_value.authenticate = mock.Mock(
            side_effect=requests.ConnectionError
        )
        backend = FreeIpaRpcAuthBackend()
        with pytest.raises(Exception):
            backend.authenticate(
                username=self.username,
                password=self.password,
            )
        # Because we can't test recursive methods, we're
        # just asserting an expected side effect
        assert mock_freeipa.call_count == 2
        assert mock_freeipa.call_args_list == [
            mock.call(
                "ipa.foo.com",
                ssl_verify="/path/to/ssl",
            ),
            mock.call(
                "ipa.failover.com",
                ssl_verify="/path/to/ssl",
            ),
        ]

    def test_update_user_groups_staff_flag(self, test_user):
        backend = FreeIpaRpcAuthBackend()
        assert not test_user.is_staff
        backend.update_user_groups(test_user, [])
        assert test_user.is_staff
    
    def test_update_user_groups_no_change_if_flag_missing(self,test_user, test_group):
        backend = FreeIpaRpcAuthBackend()
        assert test_user.groups.all().count() == 0
        backend.update_user_groups(test_user, [test_group.name])
        assert test_user.groups.all().count() == 0
    
    @override_settings(
        FREEIPA_AUTH_UPDATE_USER_GROUPS=True
    )
    def test_update_user_groups_flag_set(self, test_user, test_group, test_group2):
        backend = FreeIpaRpcAuthBackend()
        assert test_user.groups.all().count() == 0
        backend.update_user_groups(test_user, [test_group.name, test_group2])
        assert test_user.groups.all().count() == 2
        backend.update_user_groups(test_user, [test_group.name])
        assert test_user.groups.all().count() == 1

    def test_update_user_attrs(self, test_user, mock_user_session_data):
        backend = FreeIpaRpcAuthBackend()
        assert test_user.first_name == ""
        assert test_user.last_name == ""
        assert test_user.email == ""
        test_data = mock_user_session_data.user_data
        backend.update_user_attrs(test_user, test_data)
        assert test_user.first_name == test_data["givenname"]
        assert test_user.last_name == test_data["sn"]
        assert test_user.email == test_data["mail"]

    @mock.patch('freeipa_auth.backends.FreeIpaRpcAuthBackend.update_user_attrs')
    @mock.patch('freeipa_auth.backends.FreeIpaRpcAuthBackend.update_user_groups')
    def test_update_user(self, mock_update_user_groups, mock_update_user_attrs, test_user, mock_user_session_data):
        backend = FreeIpaRpcAuthBackend()
        password = test_user.password
        backend.update_user(mock_user_session_data)
        assert not test_user.check_password(password)
        assert mock_update_user_attrs.called_with(test_user, mock_user_session_data.user_data)
        assert mock_update_user_groups.called_with(test_user, mock_user_session_data.groups)

    @override_settings(
        FREEIPA_AUTH_ALWAYS_UPDATE_USER=False
    )
    @mock.patch('freeipa_auth.backends.FreeIpaRpcAuthBackend.update_user_attrs')
    @mock.patch('freeipa_auth.backends.FreeIpaRpcAuthBackend.update_user_groups')
    def test_update_user_no_update(self, mock_update_user_groups, mock_update_user_attrs, mock_user_session_data):
        backend = FreeIpaRpcAuthBackend()
        backend.update_user(mock_user_session_data)
        mock_update_user_attrs.assert_not_called()
        mock_update_user_groups.assert_not_called()
class TestFreeIpaAuthSettings:
    @override_settings(
        FREEIPA_AUTH_SERVER="ipa.foo.com",
        FREEIPA_AUTH_SSL_VERIFY="/path/to/ssl", 
    )
    def test_no_failover_set_warning(self, caplog):
        FreeIpaAuthSettings()
        assert 'FreeIPA Failover Server is not set. Proceed with caution.' in caplog.text

    @override_settings(
        FREEIPA_AUTH_SERVER="ipa.foo.com",
        FREEIPA_AUTH_FAILOVER_SERVER="ipa.failover.com",
        FREEIPA_AUTH_SSL_VERIFY="/path/to/ssl", 
    )
    def test_failover_set_no_warning(self, caplog):
        FreeIpaAuthSettings()
        assert 'FreeIPA Failover Server is not set. Proceed with caution.' not in caplog.text
