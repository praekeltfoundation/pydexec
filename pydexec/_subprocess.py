import sys

if sys.version_info[0] < 3:
    try:
        import subprocess32 as subprocess
        has_subprocess32 = True
    except ImportError:
        import warnings
        warnings.warn(
            'Running Python 2 without the subprocess32 module. Support is '
            'provided on a best-effort basis. Edge cases may be iffy.',
            RuntimeWarning)
        import subprocess
        has_subprocess32 = False
else:
    import subprocess
    has_subprocess32 = True

if sys.version_info < (3, 5):
    # Backport subprocess.run() from Python 3.5 and the CompletedProcess class.
    # Also implement versions of the exceptions used. subprocess32 has a
    # TimeoutExpired type and even Python 2.7 subprocess has a
    # CalledProcessError type but neither capture the stdout/stderr of the
    # process. The base SubprocessError type was introduced in Python 3.3.

    class SubprocessError(Exception):
        pass

    class TimeoutExpired(SubprocessError):
        """
        This exception is raised when the timeout expires while waiting for a
        child process.

        Attributes:
            cmd, output, stdout, stderr, timeout
        """
        def __init__(self, cmd, timeout, output=None, stderr=None):
            self.cmd = cmd
            self.timeout = timeout
            self.output = output
            self.stderr = stderr

        def __str__(self):
            return ("Command '%s' timed out after %s seconds" %
                    (self.cmd, self.timeout))

        @property
        def stdout(self):
            return self.output

        @stdout.setter
        def stdout(self, value):
            # There's no obvious reason to set this, but allow it anyway so
            # .stdout is a transparent alias for .output
            self.output = value

    class CalledProcessError(SubprocessError):
        """
        Raised when run() is called with check=True and the process
        returns a non-zero exit status.

        Attributes:
          cmd, returncode, stdout, stderr, output
        """
        def __init__(self, returncode, cmd, output=None, stderr=None):
            self.returncode = returncode
            self.cmd = cmd
            self.output = output
            self.stderr = stderr

        def __str__(self):
            return "Command '%s' returned non-zero exit status %d" % (
                        self.cmd, self.returncode)

        @property
        def stdout(self):
            """Alias for output attribute, to match stderr"""
            return self.output

        @stdout.setter
        def stdout(self, value):
            # There's no obvious reason to set this, but allow it anyway so
            # .stdout is a transparent alias for .output
            self.output = value

    class CompletedProcess(object):
        """A process that has finished running.

        This is returned by run().

        Attributes:
          args: The list or str args passed to run().
          returncode: The exit code of the process, negative for signals.
          stdout: The standard output (None if not captured).
          stderr: The standard error (None if not captured).
        """
        def __init__(self, args, returncode, stdout=None, stderr=None):
            self.args = args
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

        def __repr__(self):
            args = ['args={!r}'.format(self.args),
                    'returncode={!r}'.format(self.returncode)]
            if self.stdout is not None:
                args.append('stdout={!r}'.format(self.stdout))
            if self.stderr is not None:
                args.append('stderr={!r}'.format(self.stderr))
            return "{}({})".format(type(self).__name__, ', '.join(args))

        def check_returncode(self):
            """Raise CalledProcessError if the exit code is non-zero."""
            if self.returncode:
                raise CalledProcessError(
                    self.returncode, self.args, self.stdout, self.stderr)

    def run(*popenargs, **kwargs):
        """
        Run command with arguments and return a CompletedProcess instance.

        The returned instance will have attributes args, returncode, stdout and
        stderr. By default, stdout and stderr are not captured, and those
        attributes will be None. Pass stdout=PIPE and/or stderr=PIPE in order
        to capture them.

        If check is True and the exit code was non-zero, it raises a
        CalledProcessError. The CalledProcessError object will have the return
        code in the returncode attribute, and output & stderr attributes if
        those streams were captured.

        If timeout is given, and the process takes too long, a TimeoutExpired
        exception will be raised.

        There is an optional argument "input", allowing you to
        pass a string to the subprocess's stdin.  If you use this argument
        you may not also use the Popen constructor's "stdin" argument, as
        it will be used internally.

        The other arguments are the same as for the Popen constructor.

        If universal_newlines=True is passed, the "input" argument must be a
        string and stdout/stderr in the returned object will be strings rather
        than bytes.
        """
        # PY2: Pop the kwargs
        input = kwargs.pop('input', None)
        timeout = kwargs.pop('timeout', None)
        check = kwargs.pop('check', False)

        if input is not None:
            if 'stdin' in kwargs:
                raise ValueError(
                    'stdin and input arguments may not both be used.')
            kwargs['stdin'] = subprocess.PIPE

        if has_subprocess32:
            return _run(popenargs, kwargs, input, timeout, check)
        else:
            if timeout is not None:
                raise ValueError(
                    'Timeout not supported with Python 2 subprocess module')
            return _run_py2(popenargs, kwargs, input, check)

    def _run(popenargs, popenkwargs, input, timeout, check):
        with subprocess.Popen(*popenargs, **popenkwargs) as process:
            try:
                stdout, stderr = process.communicate(input, timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                raise TimeoutExpired(process.args, timeout, output=stdout,
                                     stderr=stderr)
            except:
                process.kill()
                process.wait()
                raise
            retcode = process.poll()
            if check and retcode:
                raise CalledProcessError(retcode, process.args,
                                         output=stdout, stderr=stderr)
        return CompletedProcess(process.args, retcode, stdout, stderr)

    def _run_py2(popenargs, popenkwargs, input, check):
        # PY2: non-subprocess32 is missing a few things...
        process = subprocess.Popen(*popenargs, **popenkwargs)

        # No Popen.args
        cmd = popenkwargs.get('args')
        if cmd is None:
            cmd = popenargs[0]

        # No __enter__()/__exit__()
        try:
            try:
                # No timeout
                stdout, stderr = process.communicate(input)
            except:
                process.kill()
                process.wait()
                raise
            retcode = process.poll()
            if check and retcode:
                raise CalledProcessError(retcode, cmd,
                                         output=stdout, stderr=stderr)
        finally:
            process.wait()
        return CompletedProcess(cmd, retcode, stdout, stderr)
else:
    from subprocess import (
        SubprocessError, TimeoutExpired, CalledProcessError, CompletedProcess,
        run)

__all__ = ['CalledProcessError', 'CompletedProcess', 'has_subprocess32', 'run',
           'subprocess', 'SubprocessError', 'TimeoutExpired']
