from __future__ import print_function

import os

from pydexec._subprocess import run as subprocess_run, subprocess
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
        popenargs, popenkwargs = self._popenargs()
        return subprocess_run(*popenargs, **popenkwargs)

    def spawn(self):
        """
        Run the command in a subprocess. Do *not* wait for it to finish.

        :rtype: ``subprocess.Popen``
        """
        popenargs, popenkwargs = self._popenargs()
        return subprocess.Popen(*popenargs, **popenkwargs)

    def _popenargs(self):
        cmd = [self._program] + self._args

        kwargs = {
            'env': self._env,
            'cwd': self._workdir,
            'preexec_fn': self._preexec_fn,
        }
        if self._user is not None:
            env = self._env.copy()
            env['HOME'] = self._user.home
            kwargs['env'] = env

        return ((cmd,), kwargs)

    def _preexec_fn(self):
        if self._user is not None:
            self._user.set_user()

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
