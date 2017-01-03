from __future__ import print_function

import os

from pydexec._subprocess import run as subprocess_run
from pydexec.user import User


class Command(object):
    def __init__(self, program):
        self._program = program
        self._args = []
        self._user = None
        self._env = dict(os.environ)
        self._workdir = os.getcwd()

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

    def arg_from_env(self, env_key, default=None, required=False, remove=True):
        """
        Convert the environment variable ``env_key`` to a program argument, if
        it is set. Note that this will remove ``env_key`` from the command's
        environment by default.

        :param env_key: environment variable name to use
        :param default: default value if the environment variable is not set
        :param required: raise an error if the environment variable is not set
        :param remove: remove the variable from the command's environment
        """
        env_val = self._arg_from_env(
            env_key, remove, default, required, 'an argument')
        return self.args(env_val) if env_val is not None else self

    def opt_from_env(self, opt_key, env_key, default=None, required=False,
                     remove=True):
        """
        Convert the environment variable ``env_key`` to the program option
        ``opt_key``, if the variable is set. Note that this will remove
        ``env_key`` from the command's environment by default.

        :param opt_key: the option to set (e.g. ``--volume``)
        :param env_key: environment variable name to use
        :param default: default value if the environment variable is not set
        :param required: raise an error if the environment variable is not set
        :param remove: remove the variable from the command's environment
        """
        env_val = self._arg_from_env(
            env_key, remove, default, required, 'option "%s"' % (opt_key,))
        return self.args(opt_key, env_val) if env_val is not None else self

    def _arg_from_env(self, env_key, remove, default, required, missing_str):
        """ Shared logic to fetch a program argument from the environment. """
        env_op = self._env.pop if remove else self._env.get
        env_val = env_op(env_key, default)

        if required and env_val is None:
            raise RuntimeError(
                'Environment variable "%s" is required to determine %s for '
                'program "%s"' % (env_key, missing_str, self._program))

        return env_val

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

    def workdir(self, directory):
        """
        Change the current working directory to the given directory path before
        executing the command. Note that, unlike the WORKDIR Dockerfile
        directive, this will not cause the specified directory to be created.
        """
        self._workdir = directory
        return self

    def run(self):
        """
        Run the command and wait for it to finish.

        :rtype: ``CompletedProcess``
        """
        cmd = [self._program] + self._args

        kwargs = {
            'env': self._env,
            'preexec_fn': self._preexec_fn,
        }
        if self._user is not None:
            env = self._env.copy()
            env['HOME'] = self._user.home
            kwargs['env'] = env

        return subprocess_run(cmd, **kwargs)

    def _preexec_fn(self):
        if self._user is not None:
            self._user.set_user()

        os.chdir(self._workdir)

    def exec_(self):
        """
        Exec the process, replacing the current process with the command.
        """
        cmd = [self._program] + self._args

        if self._user is not None:
            self._user.set_user()
            self._env['HOME'] = self._user.home

        os.chdir(self._workdir)

        os.execvpe(self._program, cmd, self._env)
