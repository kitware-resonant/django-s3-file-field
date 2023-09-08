from setuptools import setup
from setuptools.command.build_py import build_py
from setuptools.command.egg_info import egg_info
from setuptools.command.sdist import sdist

from build_js import NPM, js_prerelease

setup(
    cmdclass={
        'build_py': js_prerelease(build_py),
        'egg_info': js_prerelease(egg_info),
        'sdist': js_prerelease(sdist, strict=True),
        'jsdeps': NPM,
    },
)
