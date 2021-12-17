import pytest
import getpass
from django.contrib.auth import get_user_model
from collections import namedtuple
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group
from django.conf import settings as django_settings


@pytest.fixture
def test_user(request, db):
    """Fixture for a django db user"""

    password = "fake"
    user = get_user_model().objects.create_user(username="testuser",
                                                password=password)
    user.unhashed_password = password

    def fin():
        user.delete()
    request.addfinalizer(fin)

    return user


@pytest.fixture
def test_group(request, db):
    """Fixture for a django test group"""
    group = Group.objects.create(name="test_group")

    def fin():
        group.delete()
    request.addfinalizer(fin)

    return group


@pytest.fixture
def test_permission(request, db):
    """Fixture for a django test permission"""

    content_type = ContentType.objects.get_for_model(get_user_model())
    permission = Permission.objects.create(codename="test_permission",
                                           name="Test Permission",
                                           content_type=content_type)

    def fin():
        permission.delete()
    request.addfinalizer(fin)

    return permission


@pytest.fixture
def patch_authenticate_success(request, db, monkeypatch):
    """Fixture to patch successful authentication"""

    monkeypatch.setattr("requests.sessions.Session.request",
                        lambda *args, **kwargs:
                        namedtuple("Response", ['status_code'])(200))
    monkeypatch.setattr("freeipa_auth.freeipa_utils."
                        "FreeIpaSession._get_user_data",
                        lambda *args: None)


@pytest.fixture
def patch_authenticate_fail(request, db, monkeypatch):
    """Fixture patch a failed authentication"""

    monkeypatch.setattr("requests.sessions.Session.request",
                        lambda *args, **kwargs:
                        namedtuple("Response", ['status_code'])(401))


@pytest.fixture
def patch_remote_user_groups(request, db, monkeypatch):
    """Fixture to patch remote user groups"""

    monkeypatch.setattr("freeipa_auth.freeipa_utils.FreeIpaSession.groups",
                        ["admin", "test_group",
                         "test_permission"])


@pytest.fixture
def settings(request, db):
    """Fixture to allow for setting overrides per test case"""

    def override(**kwargs):
        for k, v in kwargs.items():
            setattr(django_settings, k, v)

        def fin():
            for k in kwargs:
                delattr(django_settings, k)

        request.addfinalizer(fin)

    django_settings.override = override
    return django_settings


@pytest.fixture
def liveserver_username(request, db):
    """Fixture to use a liveserver username"""
    return input("username: ")


@pytest.fixture
def liveserver_password(request, db):
    """Fixture to use a liveserver password"""
    return getpass.getpass("password: ")


@pytest.fixture
def liveserver(request, db):
    """Fixture to use a liveserver for testing (passed in from command line)"""
    return request.config.getoption('liveserver')
