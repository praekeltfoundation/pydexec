# pydexec

[![Build Status](https://travis-ci.org/praekeltfoundation/pydexec.svg?branch=develop)](https://travis-ci.org/praekeltfoundation/pydexec)
[![codecov](https://codecov.io/gh/praekeltfoundation/pydexec/branch/develop/graph/badge.svg)](https://codecov.io/gh/praekeltfoundation/pydexec)

Python tools for executing processes in Docker containers

`pydexec` makes it easier to replace entrypoint scripts for Docker containers that would typically be written in Bash (or Bourne shell) with scripts written in Python. Python entrypoint scripts should generally be less error-prone than shell scripts, especially when it comes to issues with string quoting. They are also generally friendlier for people to work on who aren't shell experts.

Using `pydexec` in your container only really makes sense if you are running Python software in the container, as a complete Python install can take up quite a bit of image space. Other than that, in most modes of running, `pydexec` aims to get out the way and let your process run and shouldn't consume extra resources inside the container once it has started.

## Usage
Replace your shell entrypoint scripts with Python code:
```python
#!/usr/bin/env python
from pydexec.command import Command

Command('thing-to-run-first').args('abc', 'def').run()

cmd = Command('my-executable')

(cmd.args('foo', 'bar')
    .args('--opt', 'val1', 'val2')
    .user('my-user:my-group'))

cmd.exec_()
```

Things to note:
 1. The stdout/stderr of the processes aren't collected or processed-- this is like a script: things just print to stdout/stderr.
 2. The `run()` call blocks until the process exits and raises an error if the exit code is non-zero. This is like running a command in a script with `-e` set.
 3. The `exec_()` call replaces the current process with the new one, just like `exec` in a script.

### Environment variables
A common pattern with Docker containers is to configure programs using environment variables rather than command-line options. `pydexec` offers some tools for working with environment variables that can simplify configuring programs in this way:
```python
cmd = Command('my-executable')
(cmd.arg_from_env('FOO')                 # arg with value $FOO if set
    .arg_from_env('BAR', default='bar')
        # arg with value $FOO if set, else 'bar'
    .opt_from_env('--foo', 'FOO')        # opt --foo with value $FOO if set
    .opt_from_env('--baz', 'BAZ', required=True))
        # opt --baz with value $BAZ if set, else raise an error

cmd.env_clear()  # remove all environment variables
cmd.env('FOO', 'bar')  # set $FOO='bar'
```

## Functionality
`pydexec` is still in its early stages and functionality is quite limited. Currently it is possible to:
* Build commands with an easy-to-use "builder" pattern
* Run those commands (blocking)
* Exec those commands
* Change user before running the command
* Convert environment variables into program arguments or options

## Planned functionality
* More tools for building commands that help in the common cases for Docker entrypoint scripts
* `dumb-init`/`tini`-like signal management and process reaping
* Very basic support for running concurrent processes in a container (similar to something like [Supervisor](http://supervisord.org), but lighter weight and without process restarting etc.)

## Potential functionality
* Easy configuration file templating
* ???

## Inspiration
`pydexec` aims to replace some of the small tools commonly used inside containers with a single easy-to-use Python library. Some of the design for `pydexec` was inspired by these tools and in some cases `pydexec` can act as a drop in replacement.

#### `gosu`/`su-exec`
These tools provide an easy way to switch to a different, non-root user at runtime in a container, without creating extra processes. For some explanation of why this is necessary, see the `gosu` documentation. `gosu` is a Golang implementation of this user-switching that uses chunks of code from the Docker codebase to replicate the behaviour of the `USER` command in Dockerfiles. `su-exec` performs the same function but is written in C. These two CLI tools are API compatible and can be used interchangeably.

`pydexec` adds a Python port of this functionality. The `pysu` CLI is provided that has the same API as `gosu` and `su-exec`. The same tests that are run against `gosu` are run against `pysu`. For the majority of cases it probably makes more sense to use this user-switching functionality programmatically in an entrypoint script rather than via the CLI, but the CLI is there if you need it and a `pip install pydexec` is probably easier than the install methods for the other tools.

#### Rust's `std::process::Command`
The design for `pydexec`'s `Command` class was inspired by the design of Rust's [`std::process::Command`](https://doc.rust-lang.org/std/process/struct.Command.html) struct (which, knowing Rust, was probably inspired by some other language :-p). `pydexec`'s `Command` is made a little more Docker-friendly by mimicing the behaviour of some Dockerfile commands like `USER`.

There are lots of different wrappers around Python's process handling code, especially for the `subprocess` module. A new design was chosen to create something that is better suited to Docker.

## Similar projects
#### `pyentrypoint`
The [`pyentrypoint`](https://github.com/cmehay/pyentrypoint) package also seeks to replace Docker entrypoints with Python code, but goes about it differently to `pydexec`. `pyentrypoint` allows you to define your entrypoint as a YAML configuration file. It also handles a few other things like templating configuration files and helps to link containers. It can also do things like watch configuration files for changes and reload processes if changes are detected. Overall, it looks like a cool project and you should try it out! But `pydexec` has slightly different aims...

`pydexec` does not aim to replace entrypoint *scripts* and doesn't try to define processes in configuration files-- it is primarily a library that is used programmatically. Also, there is some functionality that we're not interested in implementing; we don't/can't link containers in our infrastructure and we don't use configuration files that change within a running container. We'd probably like to add configuration file templating functionality to `pydexec` at some point, though.
