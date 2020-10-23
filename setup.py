# -*- coding: utf-8 -*-
from distutils import log
import os
import platform
from subprocess import CalledProcessError, check_call
import sys
from typing import List, Tuple
import re

from setuptools import Command, find_packages, setup
from setuptools.command.build_py import build_py
from setuptools.command.egg_info import egg_info
from setuptools.command.sdist import sdist

here = os.path.dirname(os.path.abspath(__file__))
node_root = os.path.join(here, 'client')
is_repo = os.path.exists(os.path.join(here, '.git'))

npm_path = os.pathsep.join(
    [
        os.path.join(node_root, 'node_modules', '.bin'),
        os.environ.get('PATH', os.defpath),
    ]
)


def js_prerelease(command, strict=False):
    """Decorate a command to building minified js/css prior to execution."""

    class DecoratedCommand(command):
        def run(self):
            jsdeps = self.distribution.get_command_obj('jsdeps')
            if not is_repo and all(os.path.exists(t) for t in jsdeps.targets):
                # sdist, nothing to do
                command.run(self)
                return

            try:
                self.distribution.run_command('jsdeps')
            except Exception as e:
                missing = [t for t in jsdeps.targets if not os.path.exists(t)]
                if strict or missing:
                    log.warn('rebuilding js and css failed')
                    if missing:
                        log.error('missing files: %s' % missing)
                    raise e
                else:
                    log.warn('rebuilding js and css failed (not a problem)')
                    log.warn(str(e))
            command.run(self)
            update_package_data(self.distribution)

    return DecoratedCommand


def update_package_data(distribution):
    """Update package_data to catch changes during setup."""
    build_py = distribution.get_command_obj('build_py')
    # distribution.package_data = find_package_data()
    # re-init build_py options which load package_data
    build_py.finalize_options()


class NPM(Command):
    description = 'install package.json dependencies using npm'

    user_options: List[Tuple[str, str, str]] = []

    node_modules = os.path.join(node_root, 'node_modules')

    targets = [os.path.join(here, 's3_file_field')]

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def get_npm_name(self):
        npm_name = 'npm'
        if platform.system() == 'Windows':
            npm_name = 'npm.cmd'

        return npm_name

    def has_npm(self):
        npm_name = self.get_npm_name()
        try:
            check_call([npm_name, '--version'])
            return True
        except CalledProcessError:
            return False

    def should_run_npm_install(self):
        # package_json = os.path.join(node_root, 'package.json')
        # node_modules_exists = os.path.exists(self.node_modules)
        return self.has_npm()

    def should_run_npm_build(self):
        return True

    def run(self):
        has_npm = self.has_npm()
        if not has_npm:
            log.error(
                '`npm` unavailable.  '
                "If you're running this command using sudo, make sure `npm` is available to sudo"
            )

        env = os.environ.copy()
        env['PATH'] = npm_path

        if self.should_run_npm_install():
            log.info('Installing build dependencies with npm.  This may take a while...')
            npm_name = self.get_npm_name()
            check_call([npm_name, 'install'], cwd=node_root, stdout=sys.stdout, stderr=sys.stderr)
            os.utime(self.node_modules, None)

        if self.should_run_npm_build():
            log.info('building with npm.  This may take a while...')
            npm_name = self.get_npm_name()
            check_call(
                [npm_name, 'run', 'build:widget'],
                cwd=node_root,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )

        for t in self.targets:
            if not os.path.exists(t):
                msg = 'Missing file: %s' % t
                if not has_npm:
                    msg += '\nnpm is required to build a development version of a widget extension'
                raise ValueError(msg)

        # update package data in case this created new files
        update_package_data(self.distribution)


def prerelease_local_scheme(version):
    """
    Return local scheme version unless building on master in CircleCI.

    This function returns the local scheme version number
    (e.g. 0.0.0.dev<N>+g<HASH>) unless building on CircleCI for a
    pre-release in which case it ignores the hash and produces a
    PEP440 compliant pre-release version number (e.g. 0.0.0.dev<N>).
    """
    from setuptools_scm.version import get_local_node_and_date

    if os.getenv('CI_BRANCH') == 'master':
        return ''
    else:
        return get_local_node_and_date(version)


with open('README.md') as f:
    readme = f.read()


def get_version(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    """
    init_py = open(os.path.join(package, '__init__.py')).read()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)

version = get_version('s3_file_field')


# perform the install
setup(
    name='django-s3-file-field',
    version=version,
    use_scm_version={'local_scheme': prerelease_local_scheme},
    setup_requires=['setuptools-scm'],
    description='A django widget library for securely uploading files directly to S3 (or MinIO).',
    long_description=readme,
    long_description_content_type='text/markdown',
    url='https://github.com/girder/django-s3-file-field',
    keywords=['django', 's3', 'minio', 'django-widget'],
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    license='Apache 2.0',
    python_requires='>=3.7.0',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.0',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python',
    ],
    packages=find_packages(include=['s3_file_field']),
    package_data={'': ['*.html', '*.js']},
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'django>=3',
        'djangorestframework',
    ],
    extras_require={
        'boto3': ['django-storages[boto3]', 'boto3'],
        'minio': ['django-minio-storage', 'minio'],
    },
    cmdclass={
        'build_py': js_prerelease(build_py),
        'egg_info': js_prerelease(egg_info),
        'sdist': js_prerelease(sdist, strict=True),
        'jsdeps': NPM,
    },
)
