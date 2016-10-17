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
        user = User.from_spec(u'')

        assert_that(user.uid, Equals(current_user.uid))
        assert_that(user.gid, Equals(current_user.gid))
        assert_that(user.sgroups_user, Equals(current_user.user))
        assert_that(user.home, Equals(current_user.home))

    def test_invalid_spec(self):
        with ExpectedException(ValueError,
                               r'Invalid user spec string "::"'):
            User.from_spec(u'::')

    def test_user_only_spec(self, current_user):
        user = User.from_spec(current_user.user)

        assert_that(user.uid, Equals(current_user.uid))
        assert_that(user.gid, Equals(current_user.gid))
        assert_that(user.sgroups_user, Equals(current_user.user))
        assert_that(user.home, Equals(current_user.home))

    def test_uid_only_spec(self, current_user):
        user = User.from_spec(str(current_user.uid))

        assert_that(user.uid, Equals(current_user.uid))
        assert_that(user.gid, Equals(current_user.gid))
        assert_that(user.sgroups_user, Equals(current_user.user))
        assert_that(user.home, Equals(current_user.home))

    def test_group_only_spec(self, current_user):
        user = User.from_spec(u':%s' % (current_user.group,))

        assert_that(user.uid, Equals(current_user.uid))
        assert_that(user.gid, Equals(current_user.gid))
        # Explicit group, no supplementary groups user
        assert_that(user.sgroups_user, Is(None))
        assert_that(user.home, Equals(current_user.home))

    def test_gid_only_spec(self, current_user):
        user = User.from_spec(u':%s' % (current_user.gid,))

        assert_that(user.uid, Equals(current_user.uid))
        assert_that(user.gid, Equals(current_user.gid))
        # Explicit group, no supplementary groups user
        assert_that(user.sgroups_user, Is(None))
        assert_that(user.home, Equals(current_user.home))

    def test_user_without_passwd_spec(self):
        with ExpectedException(KeyError):
            User.from_spec(u'idonotexistihope')

    def test_uid_without_passwd_spec(self, current_user):
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
        with ExpectedException(ValueError,
                               r'uids and gids must be in range \d+-\d+'):
            User.from_spec(str(1 << 32))

    def test_gid_too_big_spec(self):
        with ExpectedException(ValueError,
                               r'uids and gids must be in range \d+-\d+'):
            User.from_spec(u':%s' % (1 << 32,))
