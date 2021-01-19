from setuptools import find_packages, setup
from setuptools.command.build_py import build_py
from setuptools.command.egg_info import egg_info
from setuptools.command.sdist import sdist

from build_js import NPM, js_prerelease


with open('README.md') as f:
    readme = f.read()

# perform the install
setup(
    name='django-s3-file-field',
    description='A django widget library for securely uploading files directly to S3 (or MinIO).',
    long_description=readme,
    long_description_content_type='text/markdown',
    url='https://github.com/girder/django-s3-file-field',
    keywords=['django', 's3', 'minio', 'django-widget'],
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    license='Apache 2.0',
    python_requires='>=3.8.0',
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
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python',
    ],
    packages=find_packages(include=['s3_file_field']),
    package_data={'': ['*.html', '*.js']},
    include_package_data=True,
    install_requires=[
        'django>=3',
        'djangorestframework',
    ],
    extras_require={
        'boto3': ['django-storages[boto3]', 'boto3'],
        'minio': ['django-minio-storage', 'minio<7'],
    },
    cmdclass={
        'build_py': js_prerelease(build_py),
        'egg_info': js_prerelease(egg_info),
        'sdist': js_prerelease(sdist, strict=True),
        'jsdeps': NPM,
    },
)
