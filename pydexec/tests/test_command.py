# -*- coding: utf-8 -*-
import sys
from subprocess import CalledProcessError

from testtools import ExpectedException
from testtools.assertions import assert_that
from testtools.matchers import Equals

from pydexec.command import Command


def captured_lines(capfd):
    """ Read the captured stdout and stderr and parse into lines. """
    out, err = capfd.readouterr()
    if sys.version_info < (3,):
        # FIXME: I'm not entirely sure how to determine the correct encoding
        # here and not sure whether the right answer comes from Python itself
        # or pytest. For now, UTF-8 seems like a safe bet.
        out = out.encode('utf-8')
        err = err.encode('utf-8')

    out_lines = out.split('\n')
    # First line of captured output should always be blank
    assert out_lines.pop() == ''

    err_lines = err.split('\n')
    assert err_lines.pop() == ''

    return out_lines, err_lines


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
