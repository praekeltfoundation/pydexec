from __future__ import print_function

import os
import sys

from pydexec.command import Command


def main(args=sys.argv):
    if len(args) <= 2:
        script = os.path.basename(args[0])
        print('Usage: %s user-spec command [args]' % (script,))
        print('   ie: %s jamie bash' % (script,))
        print("       %s nobody:root bash -c 'whoami && id'" % (script,))
        print('       %s 1000:1 id' % (script,))
        print()
        # TODO: Print version information, license
        sys.exit(1)

    # TODO: Check if command is in PATH/executable
    cmd = Command(args[2]).args(*args[3:]).user(args[1])
    cmd.exec_()


if __name__ == '__main__':
    main()
