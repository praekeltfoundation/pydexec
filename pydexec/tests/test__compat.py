import os
import sys
import tempfile
import unittest

from pydexec import _compat
from pydexec._compat import subprocess
from pydexec.tests.helpers import skipif_not_has_subprocess32

# These tests are a straight copy from cPython 3.6.0 with a few small changes:
# * Inserted all our classes & the run function from pydexec._compat
# * Annotations to have pytest skip certain tests if we don't have subprocess32
# * Style fixes for flake8
# * A base TestCase class was removed that pokes around in subprocess internals
#   to ensure that all processes have been shut down after a test. We don't do
#   that here because we're dealing with 3+ different versions of the
#   subprocess module :-/


class RunFuncTest(unittest.TestCase):
    def run_python(self, code, **kwargs):
        """Run Python code in a subprocess using subprocess.run"""
        argv = [sys.executable, "-c", code]
        return _compat.run(argv, **kwargs)

    def test_returncode(self):
        # call() function with sequence argument
        cp = self.run_python("import sys; sys.exit(47)")
        self.assertEqual(cp.returncode, 47)
        with self.assertRaises(_compat.CalledProcessError):
            cp.check_returncode()

    def test_check(self):
        with self.assertRaises(_compat.CalledProcessError) as c:
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
        with self.assertRaises(_compat.TimeoutExpired):
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
        with self.assertRaises(_compat.TimeoutExpired) as c:
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
