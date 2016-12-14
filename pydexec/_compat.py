import sys
if sys.version_info[0] < 3:
    try:
        import subprocess32 as subprocess
    except ImportError:
        import warnings
        warnings.warn(
            'Running Python 2 without the subprocess32 module. Support is '
            'offered on a best-effort basis.', RuntimeWarning)
        import subprocess
else:
    import subprocess

__all__ = ['subprocess']
