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

__all__ = ['subprocess']
