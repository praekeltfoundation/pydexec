# -*- coding: utf-8 -*-
import multiprocessing
import os
import sys
import traceback

import pytest
from testtools import ExpectedException
from testtools.assertions import assert_that
from testtools.matchers import Equals, Not

from pydexec._compat import subprocess
from pydexec.command import Command
from pydexec.tests.helpers import captured_lines


def parse_env_output(out_lines):
    """ Parse the output of the ``env`` command into a dict. """
    cmd_env = {}
    for l in out_lines:
        env_key, env_val = l.split('=', 1)
        cmd_env[env_key] = env_val
    return cmd_env


def run_cmd(cmd):
    return cmd.run()


class ExceptionProcess(multiprocessing.Process):
    """
    Multiprocessing Process that can be queried for an exception that occurred
    in the child process.
    http://stackoverflow.com/a/33599967
    """
    def __init__(self, *args, **kwargs):
        multiprocessing.Process.__init__(self, *args, **kwargs)
        self._pconn, self._cconn = multiprocessing.Pipe()
        self._exception = None

    def run(self):
        try:
            multiprocessing.Process.run(self)
            self._cconn.send(None)
        except Exception as e:
            tb = traceback.format_exc()
            self._cconn.send((e, tb))

    @property
    def exception(self):
        if self._pconn.poll():
            self._exception = self._pconn.recv()
        return self._exception


def exec_cmd(cmd):
    # Run the command in a separate process so that it can be exec-ed
    p = ExceptionProcess(target=cmd.exec_)
    p.start()
    p.join()
    if p.exception:
        error, tb = p.exception
        print(tb)
        raise error

    if p.exitcode:
        # Simulate a CalledProcessError to simplify tests
        raise subprocess.CalledProcessError(
            p.exitcode, [cmd._program] + cmd._args)
    return p.exitcode


class TestCommand(object):
    # Use pytest-style tests rather than testtools so that we can capture
    # stdout/stderr from the file descriptors.

    @pytest.fixture(scope='class', params=[run_cmd, exec_cmd])
    def runner(self, request):
        return request.param

    def test_stdout(self, capfd, runner):
        """
        When a command writes to stdout, that output should be captured and
        written to Python's stdout.
        """
        runner(Command('echo').args('Hello, World!'))

        out_lines, err_lines = captured_lines(capfd)
        assert_that(out_lines, Equals(['Hello, World!']))
        assert_that(err_lines, Equals([]))

    def test_stderr(self, capfd, runner):
        """
        When a command writes to stderr, that output should be captured and
        written to Python's stderr.
        """
        runner(Command('awk')
               .args('BEGIN { print "Hello, World!" > "/dev/stderr" }'))

        out_lines, err_lines = captured_lines(capfd)
        assert_that(out_lines, Equals([]))
        assert_that(err_lines, Equals(['Hello, World!']))

    def test_output_unicode(self, capfd, runner):
        """
        When a command writes Unicode to a standard stream, that output should
        be captured and encoded correctly.
        """
        runner(Command('echo').args('á, é, í, ó, ú, ü, ñ, ¿, ¡'))

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines, Equals(['á, é, í, ó, ú, ü, ñ, ¿, ¡']))

    def test_error(self, capfd, runner):
        """
        When a command exits with a non-zero return code, an error should be
        raised with the correct information about the result of the command.
        The stdout or stderr output should still be captured.
        """
        with ExpectedException(
            subprocess.CalledProcessError,
                'Command .*awk.* returned non-zero exit status 1'):
            runner(Command('awk').args('BEGIN { print "errored"; exit 1 }'))

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines, Equals(['errored']))

    def test_preserves_environment(self, capfd, runner):
        """
        When a command is run, the environment variables of the parent process
        are preserved.
        """
        env = dict(os.environ)
        runner(Command('env'))

        out_lines, _ = captured_lines(capfd)
        cmd_env = parse_env_output(out_lines)

        assert_that(cmd_env, Equals(env))

    @pytest.mark.skipif(os.getuid() != 0, reason='requires root')
    def test_switch_user(self, capfd, runner):
        """
        When a user is set for the command, the user should be switched to
        before the command is run.
        """
        cmd = (Command('/bin/sh')
               .args('-c', 'echo "$(id -u):$(id -g):$(id -G)"')
               .user('1000:1000'))
        runner(cmd)

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines, Equals(['1000:1000:1000']))

        # Check that we can still run as other users (haven't demoted whole
        # Python process to non-root user)
        runner(cmd.user('0:0'))
        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines, Equals(['0:0:0']))

    @pytest.mark.skipif(os.getuid() != 0, reason='requires root')
    def test_switch_user_preserves_environment(self, capfd, runner):
        """
        When a command is run and a user is set, the environment variables of
        the parent process are preserved, except for the ``HOME`` variable
        which is updated to the user's home directory path.
        """
        env = dict(os.environ)
        cmd = Command('env')
        runner(cmd.user('1000:1000'))

        out_lines, _ = captured_lines(capfd)
        cmd_env = parse_env_output(out_lines)
        expected_env = env.copy()
        expected_env['HOME'] = '/'
        assert_that(cmd_env, Equals(expected_env))

    def test_env(self, capfd, runner):
        """
        When environment variables are added to a command, those variables
        should reflect in the child process when the command is run.
        """
        runner(Command('env').env('FOO', 'bar'))

        out_lines, _ = captured_lines(capfd)
        cmd_env = parse_env_output(out_lines)
        assert_that(cmd_env['FOO'], Equals('bar'))

    def test_env_remove(self, capfd, runner):
        """
        When environment variables are removed from a command, those variables
        should not be present in the child process when the command is run.
        """
        cmd = Command('env').env('FOO', 'bar')

        runner(cmd.env_remove('FOO'))

        out_lines, _ = captured_lines(capfd)
        cmd_env = parse_env_output(out_lines)
        assert_that('FOO' in cmd_env, Equals(False))

    def test_env_clear(self, capfd, runner):
        """
        When environment variables are cleared from a command, no variables
        should be present in the child process when the command is run.
        """
        cmd = Command('env').env('FOO', 'bar')

        runner(cmd.env_clear())

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines, Equals([]))

    def test_arg_from_env(self, capfd, runner):
        """
        When a program argument is specified via an environment variable, the
        value of the argument should be determined by the environment variable
        and the variable should be removed from the environment.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        cmd.arg_from_env('HOME')  # Pick something that should be in the env
        runner(cmd)

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0), Equals(os.environ['HOME']))

        cmd_env = parse_env_output(out_lines)
        assert_that('HOME' in cmd_env, Equals(False))

    def test_arg_from_env_not_present(self, capfd, runner):
        """
        When a program argument is specified via an environment variable, but
        the variable is not present in the environment, the argument should not
        be set.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        cmd.arg_from_env('DOESNOTEXIST')
        runner(cmd)

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0), Equals(''))

        cmd_env = parse_env_output(out_lines)
        assert_that('DOESNOTEXIST' in cmd_env, Equals(False))

    def test_arg_from_env_no_remove(self, capfd, runner):
        """
        When a program argument is specified via an environment variable, and
        the remove option is set False, the argument should be added and the
        variable should not be removed from the environment.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        cmd.arg_from_env('HOME', remove=False)
        runner(cmd)

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0), Equals(os.environ['HOME']))

        cmd_env = parse_env_output(out_lines)
        assert_that(cmd_env['HOME'], Equals(os.environ['HOME']))

    def test_arg_from_env_default(self, capfd, runner):
        """
        When a program argument is specified via an environment variable, and a
        default value is provided, then if the variable is not set, the default
        value should be used as the program argument.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        cmd.arg_from_env('DOESNOTEXIST', default='foobar')
        runner(cmd)

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0), Equals('foobar'))

        # Make extra sure the env variable isn't there
        cmd_env = parse_env_output(out_lines)
        assert_that('DOESNOTEXIST' in cmd_env, Equals(False))

    def test_arg_from_env_required(self):
        """
        When a program argument is specified via an environment variable, and
        the required option is set True, then if the variable is not set, an
        exception should be raised.
        """
        with ExpectedException(
            RuntimeError,
            'Environment variable "DOESNOTEXIST" is required to determine an '
                'argument for program "/bin/sh"'):
            Command('/bin/sh').arg_from_env('DOESNOTEXIST', required=True)

    def test_opt_from_env(self, capfd, runner):
        """
        When a program option is specified via an environment variable, the
        value of the option should be determined by the environment variable
        and the variable should be removed from the environment.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        cmd.opt_from_env('--home', 'HOME')
        runner(cmd)

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0),
                    Equals('--home %s' % (os.environ['HOME']),))

        cmd_env = parse_env_output(out_lines)
        assert_that('HOME' in cmd_env, Equals(False))

    def test_opt_from_env_not_present(self, capfd, runner):
        """
        When a program option is specified via an environment variable, but the
        variable is not present in the environment, the option should not be
        set.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        cmd.opt_from_env('--home', 'DOESNOTEXIST')
        runner(cmd)

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0), Equals(''))

        cmd_env = parse_env_output(out_lines)
        assert_that('DOESNOTEXIST' in cmd_env, Equals(False))

    def test_opt_from_env_no_remove(self, capfd, runner):
        """
        When a program option is specified via an environment variable, and the
        remove option is set False, the option should be added and the variable
        should not be removed from the environment.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        cmd.opt_from_env('--home', 'HOME', remove=False)
        runner(cmd)

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0),
                    Equals('--home %s' % (os.environ['HOME']),))

        cmd_env = parse_env_output(out_lines)
        assert_that(cmd_env['HOME'], Equals(os.environ['HOME']))

    def test_opt_from_env_default(self, capfd, runner):
        """
        When a program option is specified via an environment variable, and a
        default value is provided, then if the variable is not set, the default
        value should be used as the program option.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        cmd.opt_from_env('--home', 'DOESNOTEXIST', default='foobar')
        runner(cmd)

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0), Equals('--home foobar'))

        # Make extra sure the env variable isn't there
        cmd_env = parse_env_output(out_lines)
        assert_that('DOESNOTEXIST' in cmd_env, Equals(False))

    def test_opt_from_env_required(self):
        """
        When a program option is specified via an environment variable, and the
        required option is set True, then if the variable is not set, an
        exception should be raised.
        """
        with ExpectedException(
            RuntimeError,
            'Environment variable "DOESNOTEXIST" is required to determine '
                'option "--home" for program "/bin/sh"'):
            Command('/bin/sh').opt_from_env('--home', 'DOESNOTEXIST',
                                            required=True)

    def test_workdir_changes_directory(self, capfd, tmpdir, runner):
        """
        When a directory is specified as the 'workdir' for a command, the
        command's subprocess should be executed with the current working
        directory as the specified directory.
        """
        cwd = os.getcwd()

        runner(Command('/bin/pwd').workdir(str(tmpdir)))

        out_lines, _ = captured_lines(capfd)
        child_cwd = out_lines.pop(0)
        assert_that(child_cwd, Equals(str(tmpdir)))

        # Assert only the working directory of the child process has changed
        assert_that(child_cwd, Not(Equals(cwd)))
        assert_that(cwd, Equals(os.getcwd()))

    def test_workdir_inherited(self, capfd, runner):
        """
        When a command is run its child process should inherit the current
        working directory.
        """
        cwd = os.getcwd()

        runner(Command('/bin/pwd'))

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0), Equals(cwd))

    def test_workdir_set_at_command_creation(self, capfd, tmpdir, runner):
        """
        When a command is run its child process should inherit the current
        working directory at the time the Command object is initialised and
        changes to the parent process's current working directory should have
        no effect on the command.
        """
        old_cwd = os.getcwd()
        new_cwd = str(tmpdir)

        # Command created before chdir
        cmd = Command('/bin/pwd')

        # Change parent process's current working directory
        os.chdir(new_cwd)
        assert_that(os.getcwd(), Equals(new_cwd))

        runner(cmd)
        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0), Equals(old_cwd))

    def test_workdir_does_not_exist_exec(self, capfd):
        """
        When the command is run and the specified workdir does not exist, an
        error is raised.
        """
        if sys.version_info[0] < 3:
            exception = OSError
        else:
            exception = FileNotFoundError  # noqa: F821
        with ExpectedException(
            exception,
                r"\[Errno 2\] No such file or directory: 'DOESNOTEXIST'"):
            exec_cmd(Command('/bin/pwd').workdir('DOESNOTEXIST'))

    def test_workdir_does_not_exist_run(self, capfd):
        """
        When the command is run and the specified workdir does not exist, an
        error is raised.
        """
        if sys.version_info < (3, 3):
            exception = RuntimeError
        else:
            exception = subprocess.SubprocessError
        with ExpectedException(
                exception, r'Exception occurred in preexec_fn\.'):
            run_cmd(Command('/bin/pwd').workdir('DOESNOTEXIST'))
