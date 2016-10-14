import grp
import os
import pwd

MIN_ID = 0
MAX_ID = 1 << 31 - 1  # 32-bit compatibility, apparently


def _to_id(arg):
    _id = int(arg)
    if _id < MIN_ID or _id > MAX_ID:
        raise ValueError(
            'uids and gids must be in range %d-%d' % (MIN_ID, MAX_ID))
    return _id


class User(object):
    def __init__(self, uid, gid, sgroups_user, home):
        self.uid = uid
        self.gid = gid
        self.sgroups_user = sgroups_user
        self.home = home

    def set_user(self, env=os.environ):
        if self.sgroups_user is not None:
            os.initgroups(self.sgroups_user, self.gid)
        else:
            os.setgroups([self.gid])

        os.setgid(self.gid)
        os.setuid(self.uid)

        env['HOME'] = self.home

    @classmethod
    def from_spec(cls, user_spec):
        """
        Initialise user information from a "user spec". This code is
        essentially a Python port of gosu or su-exec (but cleaned up quite a
        bit).

        :param user_spec:
            The user spec is of the same form as is used in the ``USER``
            command in a Dockerfile: [user][:group] where ``user`` is either a
            user name or UID and ``group`` is either a group name or GID. Both
            ``user`` and ``group`` are optional.
        """
        spec_parts = user_spec.split(':')
        if len(spec_parts) == 1:
            user_arg = user_spec
            group_arg = ''
        elif len(spec_parts) == 2:
            user_arg, group_arg = spec_parts
        else:
            raise ValueError('Invalid user spec string "%s"' % (user_spec,))

        if user_arg:
            if user_arg.isdigit():
                # user_arg looks like a UID, treat it as such
                uid = _to_id(user_arg)
                try:
                    passwd = pwd.getpwuid(uid)
                except KeyError:
                    # UID without a passwd entry
                    passwd = None
            else:
                # user_arg looks like a username, it must have a passwd entry
                passwd = pwd.getpwnam(user_arg)
                uid = passwd.pw_uid
        else:
            uid = os.getuid()
            passwd = pwd.getpwuid(uid)

        sgroups_user = None
        if group_arg:
            if group_arg.isdigit():
                # group_arg looks like a GID, treat it as such
                gid = _to_id(group_arg)
            else:
                # group_arg looks like a group, it must have a groups entry
                gid = grp.getgrnam(group_arg).gr_gid
        else:
            if passwd is not None:
                gid = passwd.pw_gid
                # Set the supplementary groups username if the GID is implicit
                sgroups_user = passwd.pw_name
            else:
                gid = os.getgid()

        home = passwd.pw_dir if passwd is not None else '/'

        return User(uid, gid, sgroups_user, home)
