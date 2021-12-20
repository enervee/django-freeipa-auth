import pytest
import requests

from unittest import mock
from django.test import override_settings
from django.contrib.auth import backends

from freeipa_auth.backends import FreeIpaRpcAuthBackend


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

