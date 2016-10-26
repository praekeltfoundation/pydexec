# -*- coding: utf-8 -*-
import os
from multiprocessing import Process
from subprocess import CalledProcessError

import pytest
from testtools import ExpectedException
from testtools.assertions import assert_that
from testtools.matchers import Equals

from pydexec.command import Command
from pydexec.tests.helpers import captured_lines


def parse_env_output(out_lines):
    """ Parse the output of the ``env`` command into a dict. """
    cmd_env = {}
    for l in out_lines:
        env_key, env_val = l.split('=', 1)
        cmd_env[env_key] = env_val
    return cmd_env


class _CommonCommandTests(object):
    # Use pytest-style tests rather than testtools so that we can capture
    # stdout/stderr from the file descriptors.

    def execute(self, cmd):
        """ Execute the given Command object. """
        raise NotImplementedError()

    def test_stdout(self, capfd):
        """
        When a command writes to stdout, that output should be captured and
        written to Python's stdout.
        """
        self.execute(Command('echo').args('Hello, World!'))

        out_lines, err_lines = captured_lines(capfd)
        assert_that(out_lines, Equals(['Hello, World!']))
        assert_that(err_lines, Equals([]))

    def test_stderr(self, capfd):
        """
        When a command writes to stderr, that output should be captured and
        written to Python's stderr.
        """
        self.execute(Command('awk')
                     .args('BEGIN { print "Hello, World!" > "/dev/stderr" }'))

        out_lines, err_lines = captured_lines(capfd)
        assert_that(out_lines, Equals([]))
        assert_that(err_lines, Equals(['Hello, World!']))

    def test_output_unicode(self, capfd):
        """
        When a command writes Unicode to a standard stream, that output should
        be captured and encoded correctly.
        """
        self.execute(Command('echo').args('á, é, í, ó, ú, ü, ñ, ¿, ¡'))

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines, Equals(['á, é, í, ó, ú, ü, ñ, ¿, ¡']))

    def test_error(self, capfd):
        """
        When a command exits with a non-zero return code, an error should be
        raised with the correct information about the result of the command.
        The stdout or stderr output should still be captured.
        """
        with ExpectedException(
            CalledProcessError,
                'Command .*awk.* returned non-zero exit status 1'):
            self.execute(
                Command('awk').args('BEGIN { print "errored"; exit 1 }'))

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines, Equals(['errored']))

    def test_preserves_environment(self, capfd):
        """
        When a command is run, the environment variables of the parent process
        are preserved.
        """
        env = dict(os.environ)
        self.execute(Command('env'))

        out_lines, _ = captured_lines(capfd)
        cmd_env = parse_env_output(out_lines)

        assert_that(cmd_env, Equals(env))

    @pytest.mark.skipif(os.getuid() != 0, reason='requires root')
    def test_switch_user(self, capfd):
        """
        When a user is set for the command, the user should be switched to
        before the command is run.
        """
        cmd = (Command('/bin/sh')
               .args('-c', 'echo "$(id -u):$(id -g):$(id -G)"')
               .user('1000:1000'))
        self.execute(cmd)

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines, Equals(['1000:1000:1000']))

        # Check that we can still run as other users (haven't demoted whole
        # Python process to non-root user)
        self.execute(cmd.user('0:0'))
        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines, Equals(['0:0:0']))

    @pytest.mark.skipif(os.getuid() != 0, reason='requires root')
    def test_switch_user_preserves_environment(self, capfd):
        """
        When a command is run and a user is set, the environment variables of
        the parent process are preserved, except for the ``HOME`` variable
        which is updated to the user's home directory path.
        """
        env = dict(os.environ)
        cmd = Command('env')
        self.execute(cmd.user('1000:1000'))

        out_lines, _ = captured_lines(capfd)
        cmd_env = parse_env_output(out_lines)
        expected_env = env.copy()
        expected_env['HOME'] = '/'
        assert_that(cmd_env, Equals(expected_env))

    def test_env(self, capfd):
        """
        When environment variables are added to a command, those variables
        should reflect in the child process when the command is run.
        """
        self.execute(Command('env').env('FOO', 'bar'))

        out_lines, _ = captured_lines(capfd)
        cmd_env = parse_env_output(out_lines)
        assert_that(cmd_env['FOO'], Equals('bar'))

    def test_env_remove(self, capfd):
        """
        When environment variables are removed from a command, those variables
        should not be present in the child process when the command is run.
        """
        cmd = Command('env').env('FOO', 'bar')

        self.execute(cmd.env_remove('FOO'))

        out_lines, _ = captured_lines(capfd)
        cmd_env = parse_env_output(out_lines)
        assert_that('FOO' in cmd_env, Equals(False))

    def test_env_clear(self, capfd):
        """
        When environment variables are cleared from a command, no variables
        should be present in the child process when the command is run.
        """
        cmd = Command('env').env('FOO', 'bar')

        self.execute(cmd.env_clear())

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines, Equals([]))

    def test_arg_from_env(self, capfd):
        """
        When a program argument is specified via an environment variable, the
        value of the argument should be determined by the environment variable
        and the variable should be removed from the environment.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        cmd.arg_from_env('HOME')  # Pick something that should be in the env
        self.execute(cmd)

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0), Equals(os.environ['HOME']))

        cmd_env = parse_env_output(out_lines)
        assert_that('HOME' in cmd_env, Equals(False))

    def test_arg_from_env_not_present(self, capfd):
        """
        When a program argument is specified via an environment variable, but
        the variable is not present in the environment, the argument should not
        be set.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        cmd.arg_from_env('DOESNOTEXIST')
        self.execute(cmd)

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0), Equals(''))

        cmd_env = parse_env_output(out_lines)
        assert_that('DOESNOTEXIST' in cmd_env, Equals(False))

    def test_arg_from_env_no_remove(self, capfd):
        """
        When a program argument is specified via an environment variable, and
        the remove option is set False, the argument should be added and the
        variable should not be removed from the environment.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        cmd.arg_from_env('HOME', remove=False)
        self.execute(cmd)

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0), Equals(os.environ['HOME']))

        cmd_env = parse_env_output(out_lines)
        assert_that(cmd_env['HOME'], Equals(os.environ['HOME']))

    def test_arg_from_env_default(self, capfd):
        """
        When a program argument is specified via an environment variable, and a
        default value is provided, then if the variable is not set, the default
        value should be used as the program argument.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        cmd.arg_from_env('DOESNOTEXIST', default='foobar')
        self.execute(cmd)

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

    def test_opt_from_env(self, capfd):
        """
        When a program option is specified via an environment variable, the
        value of the option should be determined by the environment variable
        and the variable should be removed from the environment.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        cmd.opt_from_env('--home', 'HOME')
        self.execute(cmd)

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0),
                    Equals('--home %s' % (os.environ['HOME']),))

        cmd_env = parse_env_output(out_lines)
        assert_that('HOME' in cmd_env, Equals(False))

    def test_opt_from_env_not_present(self, capfd):
        """
        When a program option is specified via an environment variable, but the
        variable is not present in the environment, the option should not be
        set.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        cmd.opt_from_env('--home', 'DOESNOTEXIST')
        self.execute(cmd)

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0), Equals(''))

        cmd_env = parse_env_output(out_lines)
        assert_that('DOESNOTEXIST' in cmd_env, Equals(False))

    def test_opt_from_env_no_remove(self, capfd):
        """
        When a program option is specified via an environment variable, and the
        remove option is set False, the option should be added and the variable
        should not be removed from the environment.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        cmd.opt_from_env('--home', 'HOME', remove=False)
        self.execute(cmd)

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0),
                    Equals('--home %s' % (os.environ['HOME']),))

        cmd_env = parse_env_output(out_lines)
        assert_that(cmd_env['HOME'], Equals(os.environ['HOME']))

    def test_opt_from_env_default(self, capfd):
        """
        When a program option is specified via an environment variable, and a
        default value is provided, then if the variable is not set, the default
        value should be used as the program option.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        cmd.opt_from_env('--home', 'DOESNOTEXIST', default='foobar')
        self.execute(cmd)

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


class TestCommandRun(_CommonCommandTests):
    """ Tests for the ``Command`` class when invoking via ``run()``. """
    def execute(self, cmd):
        cmd.run()


class TestCommandExec(_CommonCommandTests):
    """ Tests for the ``Command`` class when invoking via ``exec_()``. """
    def execute(self, cmd):
        # Run the command in a separate process so that it can be exec-ed
        p = Process(target=cmd.exec_)
        p.start()
        p.join()
        if p.exitcode:
            # Simulate a CalledProcessError to simplify tests
            raise CalledProcessError(p.exitcode, [cmd._program] + cmd._args)
        return p.exitcode
