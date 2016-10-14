from __future__ import print_function

import os
from subprocess import CalledProcessError, Popen

from pydexec.user import User


class Command(object):
    def __init__(self, program):
        self._program = program
        self._args = []
        self._user = None
        self._env = dict(os.environ)

    def args(self, *args):
        """ Add a list of extra arguments to the command. """
        self._args += list(args)
        return self

    def user(self, user):
        """
        Set the user to change to before execution. The ``user`` argument
        takes the same form as that provided to the ``USER`` command in a
        Dockerfile, so [<user>][:<group>], where both user and group are
        optional and user can be a username or UID and group can be a group
        name or GID.
        """
        self._user = User.from_spec(user)
        return self

    def run(self):
        cmd = [self._program] + self._args

        # Copy the environment as it could be changed when switching user
        env = self._env.copy()
        self._setup_user(env)

        retcode = Popen(cmd, env=env).wait()
        if retcode:
            raise CalledProcessError(retcode, cmd)

    def exec_(self):
        """
        Exec the process, replacing the current process with the command.
        """
        cmd = [self._program] + self._args

        # Don't bother copying the environment; we're about to exec
        self._setup_user(self._env)

        os.execvpe(self._program, cmd, self._env)

    def _setup_user(self, env):
        if self._user is not None:
            self._user.set_user(env)
