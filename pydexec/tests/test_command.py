# -*- coding: utf-8 -*-
import multiprocessing
import os
import sys
import traceback

import pytest
from testtools import ExpectedException
from testtools.assertions import assert_that
from testtools.matchers import Equals, Not

from pydexec.command import Command
from pydexec.tests.helpers import captured_lines, parse_env_output


def run_cmd(cmd):
    return cmd.run().returncode


def spawn_cmd(cmd):
    return cmd.spawn().wait()


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

    return p.exitcode


class TestCommand(object):
    # Use pytest-style tests rather than testtools so that we can capture
    # stdout/stderr from the file descriptors.

    @pytest.fixture(scope='class', params=[run_cmd, spawn_cmd, exec_cmd])
    def runner(self, request):
        return request.param

    def test_returns(self, runner):
        """
        When we run a process that succeeds it should complete and return an
        exit code of 0.
        """
        returncode = runner(Command('true'))
        assert_that(returncode, Equals(0))

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
        When a command exits with a non-zero return code, that exit code should
        be surfaced. The stdout or stderr output should still be captured.
        """
        returncode = runner(
            Command('awk').args('BEGIN { print "errored"; exit 1 }'))
        assert_that(returncode, Equals(1))

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

    def test_workdir_does_not_exist(self, capfd, runner):
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
            runner(Command('/bin/pwd').workdir('DOESNOTEXIST'))
