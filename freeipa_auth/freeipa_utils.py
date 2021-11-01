import requests
import logging
import json


logger = logging.getLogger(__name__)


class FreeIpaSession(object):

    """FreeIPA session constructor for RPC authentication"""

    # Base login POST headers
    login_headers = {'referer': '',
                     'Content-Type': 'application/x-www-form-urlencoded',
                     'Accept': 'text/plain'}

    # Bse session POST headers
    session_headers = {'referer': '',
                       'Content-Type': 'application/json',
                       'Accept': 'application/json'}

    # Base user specific POST data
    user_post_data = {'item': [], 'method': 'user_show',
                      'params': {'all': True, 'raw': False}}

    # Base session POST data
    session_post_data = {'id': 0, 'method': '', 'params': []}

    def __init__(self, host_server, ssl_verify=False):

        self.host_server = host_server
        self.ssl_verify = ssl_verify
        self.user = None
        self.user_is_authenticated = False
        self.user_data = None
        self.session = requests.Session()

    def authenticate(self, user, password):
        """
        Authenticates user on freeipa backend and returns the session response
        :param user: string
        :param password: string
        :return: session response
        """
        url_template = 'https://{host_server}/ipa/session/login_password'
        ipa_login_url = url_template.format(host_server=self.host_server)

        # Add the referer header
        self.login_headers['referer'] = ipa_login_url

        # Set POST data
        login_data = {'user': user, 'password': password}

        logger.debug("User is attempting to authenticate via FreeIPA...")

        response = self.session.post(ipa_login_url,
                                     headers=self.login_headers,
                                     data=login_data,
                                     verify=self.ssl_verify)

        self.user = user
        # If user is authenticated, get user_data from the freeipa server
        if response.status_code == 200:
            logger.info("User successfully authenticated via FreeIPA")
            self.user_is_authenticated = True
            self.user_data = self._get_user_data()
        else:
            logger.info("User failed to authenticate via FreeIPA")

        return response

    def make_session_request(self, post_data):
        """
        Base POST request once user is authenticated
        and a session is established
        :param post_data: post_data to update base session post data
        :return:
        """

        url_template = 'https://{host_server}/ipa/session/json'
        ipa_session_url = url_template.format(host_server=self.host_server)

        # Set the referer header
        self.session_headers['referer'] = ipa_session_url

        # Update session POST data with user specific data
        self.session_post_data.update({'method': post_data['method'],
                                       'params': [
                                           post_data['item'],
                                           post_data['params']
                                       ]})

        debug_message = 'Making {method} request to {url}'
        logger.debug(debug_message.format(method=post_data['method'],
                                          url=ipa_session_url))

        request = self.session.post(
            ipa_session_url, headers=self.session_headers,
            data=json.dumps(self.session_post_data),
            verify=self.ssl_verify
        )

        results = request.json()
        return results

    def _get_user_data(self):
        """
        Internal method to grab user data on freeipa server upon authentication
        :return:
        """

        self.user_post_data['item'] = [self.user]

        if self.user_is_authenticated:
            response = self.make_session_request(self.user_post_data)
            return response['result']['result']

    @property
    def groups(self):
        """
        Returns all groups of which currently authenticated user is a member
        :return: List of groups
        """
        return self.user_data['memberof_group'] if self.user_data else []
