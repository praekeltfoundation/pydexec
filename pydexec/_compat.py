import sys
if sys.version_info[0] < 3:
    import subprocess32 as subprocess
else:
    import subprocess

__all__ = ['subprocess']
