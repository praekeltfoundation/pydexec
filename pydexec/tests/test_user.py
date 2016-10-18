import grp
import os
import pwd
from collections import namedtuple

import pytest
from testtools import ExpectedException
from testtools.assertions import assert_that
from testtools.matchers import Equals, Is

from pydexec.user import User


UserFields = namedtuple(
    'UserFields', ['uid', 'user', 'gid', 'group', 'home'])


class TestUser(object):
    """
    Tests for the User object. These tests mostly just work with the current
    user's information so as not to require root.
    """

    @pytest.fixture
    def current_user(self):
        uid = os.getuid()
        gid = os.getgid()
        passwd = pwd.getpwuid(uid)

        return UserFields(
            uid=uid,
            user=passwd.pw_name,
            gid=gid,
            group=grp.getgrgid(gid).gr_name,
            home=passwd.pw_dir
        )

    def test_empty_spec(self, current_user):
        """
        Passing an empty string as the user spec should result in the current
        user information being initialised.
        """
        user = User.from_spec(u'')

        assert_that(user.uid, Equals(current_user.uid))
        assert_that(user.gid, Equals(current_user.gid))
        assert_that(user.sgroups_user, Equals(current_user.user))
        assert_that(user.home, Equals(current_user.home))

    def test_invalid_spec(self):
        """ Passing an invlaid user spec should raise an exception. """
        with ExpectedException(ValueError,
                               r'Invalid user spec string "::"'):
            User.from_spec(u'::')

    def test_user_only_spec(self, current_user):
        """
        Passing a username as the user spec should result in the information
        for that user being initialised.
        """
        user = User.from_spec(current_user.user)

        assert_that(user.uid, Equals(current_user.uid))
        assert_that(user.gid, Equals(current_user.gid))
        assert_that(user.sgroups_user, Equals(current_user.user))
        assert_that(user.home, Equals(current_user.home))

    def test_uid_only_spec(self, current_user):
        """
        Passing a UID as the user spec should result in the information for
        that user being initialised.
        """
        user = User.from_spec(str(current_user.uid))

        assert_that(user.uid, Equals(current_user.uid))
        assert_that(user.gid, Equals(current_user.gid))
        assert_that(user.sgroups_user, Equals(current_user.user))
        assert_that(user.home, Equals(current_user.home))

    def test_group_only_spec(self, current_user):
        """
        Passing a group name as the user spec should result in the information
        for that group being initialised and the current user being used.
        """
        user = User.from_spec(u':%s' % (current_user.group,))

        assert_that(user.uid, Equals(current_user.uid))
        assert_that(user.gid, Equals(current_user.gid))
        # Explicit group, no supplementary groups user
        assert_that(user.sgroups_user, Is(None))
        assert_that(user.home, Equals(current_user.home))

    def test_gid_only_spec(self, current_user):
        """
        Passing a GID as the user spec should result in the information for
        that group being initialised and the current user being used.
        """
        user = User.from_spec(u':%s' % (current_user.gid,))

        assert_that(user.uid, Equals(current_user.uid))
        assert_that(user.gid, Equals(current_user.gid))
        # Explicit group, no supplementary groups user
        assert_that(user.sgroups_user, Is(None))
        assert_that(user.home, Equals(current_user.home))

    def test_user_without_passwd_spec(self):
        """
        Passing a username that doesn't exist as the user spec should raise an
        exception.
        """
        with ExpectedException(KeyError):
            User.from_spec(u'idonotexistihope')

    def test_uid_without_passwd_spec(self, current_user):
        """
        Passing a UID that doesn't have a passwd entry as the user spec should
        result in a User being initialised with that UID and other default
        information.
        """
        # Very inefficiently find a UID that doesn't have a passwd entry
        uid = 1  # Start at 1 since root is usually 0
        while uid in [passwd.pw_uid for passwd in pwd.getpwall()]:
            uid += 1

        user = User.from_spec(str(uid))

        assert_that(user.uid, Equals(uid))
        assert_that(user.gid, Equals(current_user.gid))
        # No passwd entry for user, can't have username or home
        assert_that(user.sgroups_user, Is(None))
        assert_that(user.home, Equals(u'/'))

    def test_uid_too_big_spec(self):
        """ Passing a UID that is too large should raise an exception. """
        with ExpectedException(ValueError,
                               r'uids and gids must be in range \d+-\d+'):
            User.from_spec(str(1 << 32))

    def test_gid_too_big_spec(self):
        """ Passing a GID that is too large should raise an exception. """
        with ExpectedException(ValueError,
                               r'uids and gids must be in range \d+-\d+'):
            User.from_spec(u':%s' % (1 << 32,))
