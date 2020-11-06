import os
from pathlib import Path
from typing import List

SECRET_KEY = 'example-secret'

DEBUG = True

ALLOWED_HOSTS: List[str] = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    's3_file_field',
    's3ff_example.core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ]
        },
    }
]

STATIC_URL = '/static/'

ROOT_URLCONF = 's3ff_example.urls'
WSGI_APPLICATION = 's3ff_example.wsgi.application'

REST_FRAMEWORK = {
    # TODO: this works around https://github.com/girder/django-s3-file-field/issues/112
    'DEFAULT_AUTHENTICATION_CLASSES': [],
}

if 'AWS_ACCESS_KEY_ID' in os.environ:
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east1')
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
else:
    DEFAULT_FILE_STORAGE = 'minio_storage.storage.MinioMediaStorage'
    MINIO_STORAGE_ENDPOINT = 'localhost:9000'
    MINIO_STORAGE_USE_HTTPS = False
    MINIO_STORAGE_ACCESS_KEY = 'minioAccessKey'
    MINIO_STORAGE_SECRET_KEY = 'minioSecretKey'
    MINIO_STORAGE_MEDIA_BUCKET_NAME = 's3ff-example'
    MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = True
    MINIO_STORAGE_AUTO_CREATE_MEDIA_POLICY = 'READ_WRITE'
    MINIO_STORAGE_MEDIA_USE_PRESIGNED = True
