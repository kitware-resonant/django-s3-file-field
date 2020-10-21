import os

SECRET_KEY = 'test_key'

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'rest_framework',
    's3_file_field',
    'test_app',
]

ROOT_URLCONF = 'test_app.urls'

# Django will use a memory resident database
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3'}}

DEFAULT_FILE_STORAGE = 'minio_storage.storage.MinioMediaStorage'
MINIO_STORAGE_ENDPOINT = os.environ['MINIO_STORAGE_ENDPOINT']
MINIO_STORAGE_USE_HTTPS = False
MINIO_STORAGE_ACCESS_KEY = os.environ['MINIO_STORAGE_ACCESS_KEY']
MINIO_STORAGE_SECRET_KEY = os.environ['MINIO_STORAGE_SECRET_KEY']
MINIO_STORAGE_MEDIA_BUCKET_NAME = os.environ['MINIO_STORAGE_MEDIA_BUCKET_NAME']
MINIO_STORAGE_AUTO_CREATE_MEDIA_POLICY = 'READ_WRITE'
MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = True
MINIO_STORAGE_MEDIA_USE_PRESIGNED = True
