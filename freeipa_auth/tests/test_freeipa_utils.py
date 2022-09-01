import json
from unittest import mock

from freeipa_auth.freeipa_utils import FreeIpaSession


class TestFreeIpaSession:
    username = "dummy_freeipa_username"
    password = "dummy_freeipa_password"

    def test_make_session_request(self):
        """
        Asserts that #make_session_request makes a POST request
        to the session url using the configured host url and the
        given params.
        """
        session = FreeIpaSession("ipa.foo.com", "/path/to/ssl")
        mock_response = mock.Mock()
        mock_response.json = mock.Mock(return_value={
            "results": "tada"
        })
        session.session.post = mock.Mock(return_value=mock_response)
        expected_url = "https://ipa.foo.com/ipa/session/json"
        expected_headers = {**session.login_headers}
        expected_headers["referer"] = expected_url
        expected_headers["Content-Type"] = "application/json"
        expected_headers["Accept"] = "application/json"
        expected_session_post_data = {**session.session_post_data}
        expected_session_post_data["method"] = "FAKE_METHOD"
        expected_session_post_data["params"] = [
            "FAKE_ITEM",
            "FAKE_PARAMS",
        ]
        results = session.make_session_request({
            "method": "FAKE_METHOD",
            "params": "FAKE_PARAMS",
            "item": "FAKE_ITEM",
        })
        session.session.post.assert_called_once_with(
            expected_url,
            headers=expected_headers,
            data=json.dumps(expected_session_post_data),
            verify="/path/to/ssl",
            timeout=5
        )
        assert results == {"results": "tada"}

    def test_get_user_data(self):
        """
        Asserts that #_get_user_data sets user_post_data using
        the user set on the instance.
        """
        session = FreeIpaSession("ipa.foo.com")
        session.user = "some_username"
        session._get_user_data()
        assert session.user_post_data['item'] == ["some_username"]

    def test_get_user_data_authenticated_requests_data(self):
        """
        Asserts that #_get_user_data makes a request for more
        user data if the user is authenticated, and that it
        returns data from the response.
        """
        session = FreeIpaSession("ipa.foo.com")
        session.user = "some_username"
        session.user_is_authenticated = True
        session.make_session_request = mock.Mock(return_value={
            "result": {
                "result": {
                    "data": "unreal data"
                }
            }
        })
        user_data = session._get_user_data()
        session.make_session_request.assert_called_once_with(
            session.user_post_data
        )
        assert user_data == {
            "data": "unreal data"
        }

    def test_get_user_data_unauthenticated_returns_dict(self):
        """
        Asserts that #_get_user_data returns {} if the user
        is not authenticated.
        """
        session = FreeIpaSession("ipa.foo.com")
        user_data = session._get_user_data()
        assert user_data == {}
