import os

from testtools import ExpectedException
from testtools.assertions import assert_that
from testtools.matchers import Equals

from pydexec.command import Command
from pydexec.tests.helpers import captured_lines, parse_env_output
from pydexec.utils import arg_from_env, opt_from_env


class TestArgFromEnvFunc(object):
    def test_arg_from_env(self, capfd):
        """
        When a program argument is specified via an environment variable, the
        value of the argument should be determined by the environment variable
        and the variable should be removed from the environment.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        arg_from_env(cmd, 'HOME')  # Pick something that should be in the env
        cmd.run()

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0), Equals(os.environ['HOME']))

        cmd_env = parse_env_output(out_lines)
        assert_that('HOME' in cmd_env, Equals(False))

    def test_not_present(self, capfd):
        """
        When a program argument is specified via an environment variable, but
        the variable is not present in the environment, the argument should not
        be set.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        arg_from_env(cmd, 'DOESNOTEXIST')
        cmd.run()

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0), Equals(''))

        cmd_env = parse_env_output(out_lines)
        assert_that('DOESNOTEXIST' in cmd_env, Equals(False))

    def test_no_remove(self, capfd):
        """
        When a program argument is specified via an environment variable, and
        the remove option is set False, the argument should be added and the
        variable should not be removed from the environment.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        arg_from_env(cmd, 'HOME', remove=False)
        cmd.run()

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0), Equals(os.environ['HOME']))

        cmd_env = parse_env_output(out_lines)
        assert_that(cmd_env['HOME'], Equals(os.environ['HOME']))

    def test_default(self, capfd):
        """
        When a program argument is specified via an environment variable, and a
        default value is provided, then if the variable is not set, the default
        value should be used as the program argument.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        arg_from_env(cmd, 'DOESNOTEXIST', default='foobar')
        cmd.run()

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0), Equals('foobar'))

        # Make extra sure the env variable isn't there
        cmd_env = parse_env_output(out_lines)
        assert_that('DOESNOTEXIST' in cmd_env, Equals(False))

    def test_required(self):
        """
        When a program argument is specified via an environment variable, and
        the required option is set True, then if the variable is not set, an
        exception should be raised.
        """
        with ExpectedException(
            RuntimeError,
            'Environment variable "DOESNOTEXIST" is required to determine an '
                'argument for program "/bin/sh"'):
            arg_from_env(Command('/bin/sh'), 'DOESNOTEXIST', required=True)


class TestOptFromEnvFunc(object):
    def test_opt_from_env(self, capfd):
        """
        When a program option is specified via an environment variable, the
        value of the option should be determined by the environment variable
        and the variable should be removed from the environment.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        opt_from_env(cmd, '--home', 'HOME')
        cmd.run()

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0),
                    Equals('--home %s' % (os.environ['HOME']),))

        cmd_env = parse_env_output(out_lines)
        assert_that('HOME' in cmd_env, Equals(False))

    def test_not_present(self, capfd):
        """
        When a program option is specified via an environment variable, but the
        variable is not present in the environment, the option should not be
        set.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        opt_from_env(cmd, '--home', 'DOESNOTEXIST')
        cmd.run()

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0), Equals(''))

        cmd_env = parse_env_output(out_lines)
        assert_that('DOESNOTEXIST' in cmd_env, Equals(False))

    def test_no_remove(self, capfd):
        """
        When a program option is specified via an environment variable, and the
        remove option is set False, the option should be added and the variable
        should not be removed from the environment.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        opt_from_env(cmd, '--home', 'HOME', remove=False)
        cmd.run()

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0),
                    Equals('--home %s' % (os.environ['HOME']),))

        cmd_env = parse_env_output(out_lines)
        assert_that(cmd_env['HOME'], Equals(os.environ['HOME']))

    def test_default(self, capfd):
        """
        When a program option is specified via an environment variable, and a
        default value is provided, then if the variable is not set, the default
        value should be used as the program option.
        """
        cmd = Command('/bin/sh').args('-c', 'echo "$@" && env', '--')
        opt_from_env(cmd, '--home', 'DOESNOTEXIST', default='foobar')
        cmd.run()

        out_lines, _ = captured_lines(capfd)
        assert_that(out_lines.pop(0), Equals('--home foobar'))

        # Make extra sure the env variable isn't there
        cmd_env = parse_env_output(out_lines)
        assert_that('DOESNOTEXIST' in cmd_env, Equals(False))

    def test_required(self):
        """
        When a program option is specified via an environment variable, and the
        required option is set True, then if the variable is not set, an
        exception should be raised.
        """
        with ExpectedException(
            RuntimeError,
            'Environment variable "DOESNOTEXIST" is required to determine '
                'option "--home" for program "/bin/sh"'):
            opt_from_env(Command('/bin/sh'), '--home', 'DOESNOTEXIST',
                         required=True)
