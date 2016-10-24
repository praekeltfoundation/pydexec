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
        self._args.extend(args)
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

    def env_arg(self, env_key, default=None, required=False, remove=True):
        """
        Add an argument with the value of the ``env_key`` environment variable
        if it is set.

        :param env_key: environment variable name to use
        :param default: default value if the environment variable is not set
        :param required: raise an error if the environment variable is not set
        :param remove: remove the variable from the command's environment
        """
        env_val = self._env_get(env_key, remove, default)
        if env_val is not None:
            self._args.append(env_val)
        elif required:
            raise RuntimeError(
                'Environment variable "%s" is required to determine an '
                'argument for program "%s"' % (env_key, self._program))
        return self

    def env_opt(self, opt_key, env_key, default=None, required=False,
                remove=True):
        """
        Add the option ``opt_key`` with the value of the ``env_key``
        environment variable if it is set.

        :param opt_key: the option to set (e.g. ``--volume``)
        :param env_key: environment variable name to use
        :param default: default value if the environment variable is not set
        :param required: raise an error if the environment variable is not set
        :param remove: remove the variable from the command's environment
        """
        env_val = self._env_get(env_key, remove, default)
        if env_val is not None:
            self._args.extend([opt_key, env_val])
        elif required:
            raise RuntimeError(
                'Environment variable "%s" is required to determine option '
                '"%s" for program "%s"' % (env_key, opt_key, self._program))
        return self

    def _env_get(self, env_key, remove=False, default=None):
        env_op = self._env.pop if remove else self._env.get
        return env_op(env_key, default)

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
