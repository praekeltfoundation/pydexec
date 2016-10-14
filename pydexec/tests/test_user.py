import grp
import os
import pwd

from testtools import ExpectedException, TestCase
from testtools.matchers import Equals, Is

from pydexec.user import User


class TestUser(TestCase):

    def setUp(self):
        super(TestUser, self).setUp()
        self.current_uid = os.getuid()
        self.current_gid = os.getgid()

        passwd = pwd.getpwuid(self.current_uid)
        self.current_user = passwd.pw_name
        self.current_home = passwd.pw_dir

        group = grp.getgrgid(self.current_gid)
        self.current_group = group.gr_name

    def test_empty_spec(self):
        user = User.from_spec(u'')

        self.assertThat(user.uid, Equals(self.current_uid))
        self.assertThat(user.gid, Equals(self.current_gid))
        self.assertThat(user.sgroups_user, Equals(self.current_user))
        self.assertThat(user.home, Equals(self.current_home))

    def test_invalid_spec(self):
        with ExpectedException(ValueError,
                               r'Invalid user spec string "::"'):
            User.from_spec(u'::')

    def test_user_only_spec(self):
        user = User.from_spec(self.current_user)

        self.assertThat(user.uid, Equals(self.current_uid))
        self.assertThat(user.gid, Equals(self.current_gid))
        self.assertThat(user.sgroups_user, Equals(self.current_user))
        self.assertThat(user.home, Equals(self.current_home))

    def test_uid_only_spec(self):
        user = User.from_spec(str(self.current_uid))

        self.assertThat(user.uid, Equals(self.current_uid))
        self.assertThat(user.gid, Equals(self.current_gid))
        self.assertThat(user.sgroups_user, Equals(self.current_user))
        self.assertThat(user.home, Equals(self.current_home))

    def test_group_only_spec(self):
        user = User.from_spec(u':%s' % (self.current_group,))

        self.assertThat(user.uid, Equals(self.current_uid))
        self.assertThat(user.gid, Equals(self.current_gid))
        # Explicit group, no supplementary groups user
        self.assertThat(user.sgroups_user, Is(None))
        self.assertThat(user.home, Equals(self.current_home))

    def test_gid_only_spec(self):
        user = User.from_spec(u':%s' % (self.current_gid,))

        self.assertThat(user.uid, Equals(self.current_uid))
        self.assertThat(user.gid, Equals(self.current_gid))
        # Explicit group, no supplementary groups user
        self.assertThat(user.sgroups_user, Is(None))
        self.assertThat(user.home, Equals(self.current_home))

    def test_user_without_passwd_spec(self):
        with ExpectedException(KeyError):
            User.from_spec(u'idonotexistihope')

    def test_uid_without_passwd_spec(self):
        # Very inefficiently find a UID that doesn't have a passwd entry
        uid = 1  # Start at 1 since root is usually 0
        while uid in [passwd.pw_uid for passwd in pwd.getpwall()]:
            uid += 1

        user = User.from_spec(str(uid))

        self.assertThat(user.uid, Equals(uid))
        self.assertThat(user.gid, Equals(self.current_gid))
        # No passwd entry for user, can't have username or home
        self.assertThat(user.sgroups_user, Is(None))
        self.assertThat(user.home, Equals(u'/'))

    def test_uid_too_big_spec(self):
        with ExpectedException(ValueError,
                               r'uids and gids must be in range \d+-\d+'):
            User.from_spec(str(1 << 32))

    def test_gid_too_big_spec(self):
        with ExpectedException(ValueError,
                               r'uids and gids must be in range \d+-\d+'):
            User.from_spec(u':%s' % (1 << 32,))
