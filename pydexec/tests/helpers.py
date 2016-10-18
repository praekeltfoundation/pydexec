import sys


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
