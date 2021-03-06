import sys
from setuptools import find_packages, setup


install_requires = []
if sys.version_info[0] < 3:
    install_requires.append('subprocess32')

setup(
    name='pydexec',
    version='0.1.0-dev',
    description='Tools for executing commands inside Docker containers',
    url='https://github.com/praekeltorg/pydexec',
    author='Jamie Hewland',
    author_email='jamie@praekelt.org',
    license='BSD-3-Clause',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        # While PyPy3 seems to 'work', we're not currently testing it due to
        # some bugs it has, so we can't quite claim to support it.
        # 'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages=find_packages(),
    install_requires=install_requires,
    entry_points={
        'console_scripts': ['pysu = pydexec.pysu:main'],
    }
)
