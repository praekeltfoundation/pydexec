import os
import subprocess

import pytest
from testtools import ExpectedException
from testtools.assertions import assert_that
from testtools.matchers import Equals, MatchesStructure

from pydexec.pysu import main
from pydexec.tests.helpers import captured_lines


def _id(*args):
    """ Run an ``id`` command. """
    return _cmd('id', *args)


def pysu_real_ids(user_spec):
    # Don't allow errors (set -e)
    return _cmd('pysu', user_spec, '/bin/sh', '-c',
                'set -e; echo "$(id -u):$(id -g):$(id -G)"')


def pysu_real_names(user_spec):
    # Allow errors due to unknown IDs
    return _cmd('pysu', user_spec, '/bin/sh', '-c',
                'echo "$(id -un):$(id -gn):$(id -Gn)"')


def _cmd(*args):
    return subprocess.check_output(args).strip().decode('utf-8')


def pysu_env_home(user_spec):
    env = _cmd('pysu', user_spec, 'env')
    return [line for line in env.split() if line.startswith('HOME=')]


def gosu_t(user_spec, expec1, expec2):
    assert_that(pysu_real_ids(user_spec), Equals(expec1))
    assert_that(pysu_real_names(user_spec), Equals(expec2))


@pytest.mark.skipif(os.getuid() != 0, reason='requires root')
def test_gosu():
    """
    Roughly emulate the gosu test suite, but with more Python and less Docker:
    https://github.com/tianon/gosu/blob/1.10/Dockerfile.test

    One major difference between this and the gosu tests is that the gosu tests
    run under the 'nobody' user after setting the setuid bit on the gosu binary
    to allow the user to be changed. This is difficult to do with a thing that
    isn't a single compiled binary like gosu, so we just run everything as root
    here.

    These tests will only work on a standard Linux host with known users/groups
    like "games" and "daemon".
    """
    # gosu-t 0 "0:0:$(id -G root)" "root:root:$(id -Gn root)"
    gosu_t('0', '0:0:%s' % (_id('-G', 'root'),), 'root:root:%s' % (_id('-Gn', 'root'),))  # noqa: E501
    # gosu-t 0:0 '0:0:0' 'root:root:root'
    gosu_t('0:0', '0:0:0', 'root:root:root')
    # gosu-t root "0:0:$(id -G root)" "root:root:$(id -Gn root)"
    gosu_t('root', '0:0:%s' % (_id('-G', 'root'),), 'root:root:%s' % (_id('-Gn', 'root'),))  # noqa: E501
    # gosu-t 0:root '0:0:0' 'root:root:root'
    gosu_t('0:root', '0:0:0', 'root:root:root')
    # gosu-t root:0 '0:0:0' 'root:root:root'
    gosu_t('root:0', '0:0:0', 'root:root:root')
    # gosu-t root:root '0:0:0' 'root:root:root'
    gosu_t('root:root', '0:0:0', 'root:root:root')
    # gosu-t 1000 "1000:$(id -g):$(id -g)" "1000:$(id -gn):$(id -gn)"
    gosu_t('1000', '1000:%s:%s' % (_id('-g'), _id('-g')), '1000:%s:%s' % (_id('-gn'), _id('-gn')))  # noqa: E501
    # gosu-t 0:1000 '0:1000:1000' 'root:1000:1000'
    gosu_t('0:1000', '0:1000:1000', 'root:1000:1000')
    # gosu-t 1000:1000 '1000:1000:1000' '1000:1000:1000'
    gosu_t('1000:1000', '1000:1000:1000', '1000:1000:1000')
    # gosu-t root:1000 '0:1000:1000' 'root:1000:1000'
    gosu_t('root:1000', '0:1000:1000', 'root:1000:1000')
    # gosu-t 1000:root '1000:0:0' '1000:root:root'
    gosu_t('1000:root', '1000:0:0', '1000:root:root')
    # gosu-t 1000:daemon "1000:$(id -g daemon):$(id -g daemon)" '1000:daemon:daemon'  # noqa: E501
    gosu_t('1000:daemon', '1000:%s:%s' % (_id('-g', 'daemon'), _id('-g', 'daemon')), '1000:daemon:daemon')  # noqa: E501
    # gosu-t games "$(id -u games):$(id -g games):$(id -G games)" 'games:games:games'  # noqa: E501
    gosu_t('games', '%s:%s:%s' % (_id('-u', 'games'), _id('-g', 'games'), _id('-G', 'games')), 'games:games:games')  # noqa: E501
    # gosu-t games:daemon "$(id -u games):$(id -g daemon):$(id -g daemon)" 'games:daemon:daemon'  # noqa: E501
    gosu_t('games:daemon', '%s:%s:%s' % (_id('-u', 'games'), _id('-g', 'daemon'), _id('-g', 'daemon')), 'games:daemon:daemon')  # noqa: E501

    # gosu-t 0: "0:0:$(id -G root)" "root:root:$(id -Gn root)"
    gosu_t('0', '0:0:%s' % (_id('-G', 'root'),), 'root:root:%s' % (_id('-Gn', 'root'),))  # noqa: E501
    # gosu-t '' "$(id -u):$(id -g):$(id -G)" "$(id -un):$(id -gn):$(id -Gn)"
    gosu_t('', '%s:%s:%s' % (_id('-u'), _id('-g'), _id('-G')), 'root:root:%s' % (_id('-Gn', 'root'),))  # noqa: E501
    # gosu-t ':0' "$(id -u):0:0" "$(id -un):root:root"
    gosu_t(':0', '%s:0:0' % (_id('-u'),), '%s:root:root' % (_id('-un'),))

    # [ "$(gosu 0 env | grep '^HOME=')" = 'HOME=/root' ]
    assert_that(pysu_env_home('0'), Equals(['HOME=/root']))
    # [ "$(gosu 0:0 env | grep '^HOME=')" = 'HOME=/root' ]
    assert_that(pysu_env_home('0:0'), Equals(['HOME=/root']))
    # [ "$(gosu root env | grep '^HOME=')" = 'HOME=/root' ]
    assert_that(pysu_env_home('root'), Equals(['HOME=/root']))
    # [ "$(gosu 0:root env | grep '^HOME=')" = 'HOME=/root' ]
    assert_that(pysu_env_home('0:root'), Equals(['HOME=/root']))
    # [ "$(gosu root:0 env | grep '^HOME=')" = 'HOME=/root' ]
    assert_that(pysu_env_home('root:0'), Equals(['HOME=/root']))
    # [ "$(gosu root:root env | grep '^HOME=')" = 'HOME=/root' ]
    assert_that(pysu_env_home('root:root'), Equals(['HOME=/root']))
    # [ "$(gosu 0:1000 env | grep '^HOME=')" = 'HOME=/root' ]
    assert_that(pysu_env_home('0:1000'), Equals(['HOME=/root']))
    # [ "$(gosu root:1000 env | grep '^HOME=')" = 'HOME=/root' ]
    assert_that(pysu_env_home('root:1000'), Equals(['HOME=/root']))
    # [ "$(gosu 1000 env | grep '^HOME=')" = 'HOME=/' ]
    assert_that(pysu_env_home('1000'), Equals(['HOME=/']))
    # [ "$(gosu 1000:0 env | grep '^HOME=')" = 'HOME=/' ]
    assert_that(pysu_env_home('1000:0'), Equals(['HOME=/']))
    # [ "$(gosu 1000:root env | grep '^HOME=')" = 'HOME=/' ]
    assert_that(pysu_env_home('1000:root'), Equals(['HOME=/']))
    # [ "$(gosu games env | grep '^HOME=')" = 'HOME=/usr/games' ]
    assert_that(pysu_env_home('games'), Equals(['HOME=/usr/games']))
    # [ "$(gosu games:daemon env | grep '^HOME=')" = 'HOME=/usr/games' ]
    assert_that(pysu_env_home('games:daemon'), Equals(['HOME=/usr/games']))


def test_help_message(capfd):
    """
    When the pysu command is run with the wrong number of arguments, it should
    print the usage information and exit with code 1.
    """
    with ExpectedException(SystemExit, MatchesStructure(code=Equals(1))):
        main(['pysu', '--help'])

    out_lines, _ = captured_lines(capfd)
    assert_that(out_lines, Equals([
        'Usage: pysu user-spec command [args]',
        '   ie: pysu jamie bash',
        "       pysu nobody:root bash -c 'whoami && id'",
        '       pysu 1000:1 id',
        '',
    ]))
