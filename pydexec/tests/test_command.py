# -*- coding: utf-8 -*-
import os
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


class TestCommand(object):
    # Use pytest-style tests rather than testtools so that we can capture
    # stdout/stderr from the file descriptors.

    def test_run_stdout(self, capfd):
        """
        When a command writes to stdout, that output should be captured and
        written to Python's stdout.
        """
        Command('echo').args('Hello, World!').run()

        out_lines, err_lines = captured_lines(capfd)
        assert_that(out_lines, Equals(['Hello, World!']))
        assert_that(err_lines, Equals([]))

    def test_run_stderr(self, capfd):
        """
        When a command writes to stderr, that output should be captured and
        written to Python's stderr.
        """
        (Command('awk')
            .args('BEGIN { print "Hello, World!" > "/dev/stderr" }').run())

        out_lines, err_lines = captured_lines(capfd)
        assert_that(out_lines, Equals([]))
        assert_that(err_lines, Equals(['Hello, World!']))

    def test_run_output_unicode(self, capfd):
        """
        When a command writes Unicode to a standard stream, that output should
        be captured and encoded correctly.
        """
        Command('echo').args('á, é, í, ó, ú, ü, ñ, ¿, ¡').run()

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines, Equals(['á, é, í, ó, ú, ü, ñ, ¿, ¡']))

    def test_run_error(self, capfd):
        """
        When a command exits with a non-zero return code, an error should be
        raised with the correct information about the result of the command.
        The stdout or stderr output should still be captured.
        """
        with ExpectedException(
            CalledProcessError,
                'Command .*awk.* returned non-zero exit status 1'):
            Command('awk').args('BEGIN { print "errored"; exit 1 }').run()

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines, Equals(['errored']))

    def test_run_preserves_environment(self, capfd):
        """
        When a command is run, the environment variables of the parent process
        are preserved.
        """
        env = dict(os.environ)
        Command('env').run()

        out_lines, _ = captured_lines(capfd)
        cmd_env = parse_env_output(out_lines)

        assert_that(cmd_env, Equals(env))

    @pytest.mark.skipif(os.getuid() != 0, reason='requires root')
    def test_run_switch_user(self, capfd):
        """
        When a user is set for the command, the user should be switched to
        before the command is run.
        """
        cmd = (Command('/bin/sh')
               .args('-c', 'echo "$(id -u):$(id -g):$(id -G)"')
               .user('1000:1000'))
        cmd.run()

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines, Equals(['1000:1000:1000']))

        # Check that we can still run as other users (haven't demoted whole
        # Python process to non-root user)
        cmd.user('0:0').run()
        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines, Equals(['0:0:0']))

    @pytest.mark.skipif(os.getuid() != 0, reason='requires root')
    def test_run_switch_user_preserves_environment(self, capfd):
        """
        When a command is run and a user is set, the environment variables of
        the parent process are preserved, except for the ``HOME`` variable
        which is updated to the user's home directory path.
        """
        env = dict(os.environ)
        cmd = Command('env')
        cmd.user('1000:1000').run()

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
        Command('env').env('FOO', 'bar').run()

        out_lines, _ = captured_lines(capfd)
        cmd_env = parse_env_output(out_lines)
        assert_that(cmd_env['FOO'], Equals('bar'))

    def test_env_remove(self, capfd):
        """
        When environment variables are removed from a command, those variables
        should not be present in the child process when the command is run.
        """
        cmd = Command('env').env('FOO', 'bar')

        cmd.env_remove('FOO').run()

        out_lines, _ = captured_lines(capfd)
        cmd_env = parse_env_output(out_lines)
        assert_that('FOO' in cmd_env, Equals(False))

    def test_env_clear(self, capfd):
        """
        When environment variables are cleared from a command, no variables
        should be present in the child process when the command is run.
        """
        cmd = Command('env').env('FOO', 'bar')

        cmd.env_clear().run()

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines, Equals([]))
