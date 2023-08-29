from pathlib import Path

from setuptools import find_packages, setup

readme_file = Path(__file__).parent.absolute() / 'README.md'
with readme_file.open() as f:
    long_description = f.read()

setup(
    name='django-s3-file-field-client',
    description='A Python client library for django-s3-file-field.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    license='Apache 2.0',
    url='https://github.com/girder/django-s3-file-field',
    project_urls={
        'Bug Reports': 'https://github.com/girder/django-s3-file-field/issues',
        'Source': 'https://github.com/girder/django-s3-file-field',
    },
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    keywords='django girder',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Django :: 3.2',
        'Framework :: Django :: 4.1',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python',
    ],
    python_requires='>=3.8',
    install_requires=['requests'],
    packages=find_packages(),
    # Package data is required for the py.typed file
    include_package_data=True,
)
