import os
import sys
import tempfile
import unittest

from testtools.assertions import assert_that
from testtools.matchers import Equals, MatchesRegex

from pydexec._subprocess import (
    CalledProcessError, CompletedProcess, run, subprocess, TimeoutExpired)
from pydexec.tests.helpers import (
    skipif_has_subprocess32, skipif_not_has_subprocess32)

# NOTE: None of the tests in this file *need* to be run on Python 3.5+ but we
# do so anyway to ensure compatibility between Python versions.


class RunFuncTest(unittest.TestCase):
    # These tests are a straight copy from cPython 3.5.0 with a few changes:
    # * Inserted all our classes & the run function from pydexec._compat
    # * Annotations to have pytest skip certain tests if we don't have
    #   subprocess32
    # * Style fixes for flake8
    # * A base TestCase class was removed that pokes around in subprocess
    #   internals to ensure that all processes have been shut down after a
    #   test. We don't do that here because we're dealing with 3+ different
    #   versions of the subprocess module :-/
    # * A test was added (test_communicate_failure) to ensure coverage of the
    #   failure case where an error occurs while communicating with the
    #   process.
    # * A test was added for the case where the user tries to provide a timeout
    #   value but the subprocess module in use does not support timeouts.

    def run_python(self, code, **kwargs):
        """Run Python code in a subprocess using subprocess.run"""
        argv = [sys.executable, "-c", code]
        return run(argv, **kwargs)

    def test_returncode(self):
        # call() function with sequence argument
        cp = self.run_python("import sys; sys.exit(47)")
        self.assertEqual(cp.returncode, 47)
        with self.assertRaises(CalledProcessError):
            cp.check_returncode()

    def test_check(self):
        with self.assertRaises(CalledProcessError) as c:
            self.run_python("import sys; sys.exit(47)", check=True)
        self.assertEqual(c.exception.returncode, 47)

    def test_check_zero(self):
        # check_returncode shouldn't raise when returncode is zero
        cp = self.run_python("import sys; sys.exit(0)", check=True)
        self.assertEqual(cp.returncode, 0)

    @skipif_not_has_subprocess32
    def test_timeout(self):
        # run() function with timeout argument; we want to test that the child
        # process gets killed when the timeout expires.  If the child isn't
        # killed, this call will deadlock since subprocess.run waits for the
        # child.
        with self.assertRaises(TimeoutExpired):
            self.run_python("while True: pass", timeout=0.0001)

    def test_capture_stdout(self):
        # capture stdout with zero return code
        cp = self.run_python("print('BDFL')", stdout=subprocess.PIPE)
        self.assertIn(b'BDFL', cp.stdout)

    def test_capture_stderr(self):
        cp = self.run_python("import sys; sys.stderr.write('BDFL')",
                             stderr=subprocess.PIPE)
        self.assertIn(b'BDFL', cp.stderr)

    def test_check_output_stdin_arg(self):
        # run() can be called with stdin set to a file
        tf = tempfile.TemporaryFile()
        self.addCleanup(tf.close)
        tf.write(b'pear')
        tf.seek(0)
        cp = self.run_python(
                "import sys; sys.stdout.write(sys.stdin.read().upper())",
                stdin=tf, stdout=subprocess.PIPE)
        self.assertIn(b'PEAR', cp.stdout)

    def test_check_output_input_arg(self):
        # check_output() can be called with input set to a string
        cp = self.run_python(
                "import sys; sys.stdout.write(sys.stdin.read().upper())",
                input=b'pear', stdout=subprocess.PIPE)
        self.assertIn(b'PEAR', cp.stdout)

    def test_check_output_stdin_with_input_arg(self):
        # run() refuses to accept 'stdin' with 'input'
        tf = tempfile.TemporaryFile()
        self.addCleanup(tf.close)
        tf.write(b'pear')
        tf.seek(0)
        with self.assertRaises(
            ValueError,
            msg="Expected ValueError when stdin and input args supplied."
                ) as c:
            self.run_python("print('will not be run')",
                            stdin=tf, input=b'hare')
        self.assertIn('stdin', c.exception.args[0])
        self.assertIn('input', c.exception.args[0])

    @skipif_not_has_subprocess32
    def test_check_output_timeout(self):
        with self.assertRaises(TimeoutExpired) as c:
            self.run_python((
                "import sys, time\n"
                "sys.stdout.write('BDFL')\n"
                "sys.stdout.flush()\n"
                "time.sleep(3600)"),
                # Some heavily loaded buildbots (sparc Debian 3.x) require
                # this much time to start and print.
                timeout=3, stdout=subprocess.PIPE)
        self.assertEqual(c.exception.output, b'BDFL')
        # output is aliased to stdout
        self.assertEqual(c.exception.stdout, b'BDFL')

    def test_run_kwargs(self):
        newenv = os.environ.copy()
        newenv["FRUIT"] = "banana"
        cp = self.run_python((
            'import sys, os;'
            'sys.exit(33 if os.getenv("FRUIT")=="banana" else 31)'),
            env=newenv)
        self.assertEqual(cp.returncode, 33)

    def test_communicate_failure(self):
        """
        When an unexpected error occurs when communicating with the process
        (e.g. we give some non-string/bytes object as input), the error should
        be re-raised.
        """
        with self.assertRaises(TypeError) as c:
            self.run_python('foo', input=123)

        self.assertRegexpMatches(str(c.exception), r"not '?int'?")

    @skipif_has_subprocess32
    def test_py2_timeout_not_supported(self):
        """
        If a timeout is specified and we're running the Python 2 subprocess
        module, an error should be raised.
        """
        with self.assertRaises(ValueError) as c:
            self.run_python('import sys; sys.exit(0)', timeout=5)

        self.assertEqual(
            str(c.exception),
            'Timeout not supported with Python 2 subprocess module')


class TestTimeoutExpired(object):
    def test_str(self):
        error = TimeoutExpired('foo', 5)
        assert_that(str(error),
                    Equals("Command 'foo' timed out after 5 seconds"))

    def test_stdout_property(self):
        error = TimeoutExpired('foo', 5)
        error.stdout = 'bar'
        assert_that(error.stdout, Equals('bar'))
        assert_that(error.output, Equals('bar'))


class TestCalledProcessError(object):
    def test_str(self):
        error = CalledProcessError(5, 'foo')
        assert_that(
            str(error),
            # Python 3.6 adds a period to the ends of some error messages :-/
            MatchesRegex(r"Command 'foo' returned non-zero exit status 5\.?"))

    def test_stdout_property(self):
        error = CalledProcessError(5, 'foo')
        error.stdout = 'bar'
        assert_that(error.stdout, Equals('bar'))
        assert_that(error.output, Equals('bar'))


class TestCompletedProcess(object):
    def test_repr(self):
        completed_process = CompletedProcess(
            'foo', 0, stdout='bar', stderr='baz')
        assert_that(repr(completed_process), Equals(
            "CompletedProcess(args='foo', returncode=0, stdout='bar', "
            "stderr='baz')"))
