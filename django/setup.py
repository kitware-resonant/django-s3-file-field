from setuptools import setup

setup(
    name='joist',
    version='0.1',
    python_requires='>=3.7.0',
    install_requires=['boto3', 'django', 'djangorestframework', 'django-storages', 'psycopg2'],
)
