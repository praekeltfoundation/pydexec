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

    def env(self, env_key, env_val):
        """
        Add the environment variable ``env_key`` with the value ``env_val``.
        """
        self._env[env_key] = env_val
        return self

    def env_remove(self, env_key):
        """ Remove the environment variable ``env_key``. """
        del self._env[env_key]
        return self

    def env_clear(self):
        """ Clear all environment variables. """
        self._env = {}
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

        kwargs = {'env': self._env}
        if self._user is not None:
            env = self._env.copy()
            env['HOME'] = self._user.home
            kwargs = {
                'env': env,
                'preexec_fn': self._user.set_user
            }

        retcode = Popen(cmd, **kwargs).wait()
        if retcode:
            raise CalledProcessError(retcode, cmd)

    def exec_(self):
        """
        Exec the process, replacing the current process with the command.
        """
        cmd = [self._program] + self._args

        if self._user is not None:
            self._user.set_user()
            self._env['HOME'] = self._user.home

        os.execvpe(self._program, cmd, self._env)
