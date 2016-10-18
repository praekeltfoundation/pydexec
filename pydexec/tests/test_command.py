# -*- coding: utf-8 -*-
import os
from subprocess import CalledProcessError

import pytest
from testtools import ExpectedException
from testtools.assertions import assert_that
from testtools.matchers import Equals

from pydexec.command import Command
from pydexec.tests.helpers import captured_lines


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

    @pytest.mark.skipif(os.getuid() != 0, reason='requires root')
    def test_switch_user(self, capfd):
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
