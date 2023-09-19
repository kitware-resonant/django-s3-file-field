import os

import django

SECRET_KEY = "test_key"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "rest_framework",
    "s3_file_field",
    "test_app",
]

ROOT_URLCONF = "test_app.urls"

# Django will use a memory resident database
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3"}}

if django.VERSION < (5, 0):
    USE_TZ = True

if django.VERSION < (4, 2):
    DEFAULT_FILE_STORAGE = "minio_storage.storage.MinioMediaStorage"
else:
    STORAGES = {
        "default": {
            "BACKEND": "minio_storage.storage.MinioMediaStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
# Use values compatible with Docker Compose as defaults, in case environment variables are not set
MINIO_STORAGE_ENDPOINT = os.environ.get("MINIO_STORAGE_ENDPOINT", "localhost:9000")
MINIO_STORAGE_USE_HTTPS = False
MINIO_STORAGE_ACCESS_KEY = os.environ.get("MINIO_STORAGE_ACCESS_KEY", "minioAccessKey")
MINIO_STORAGE_SECRET_KEY = os.environ.get("MINIO_STORAGE_SECRET_KEY", "minioSecretKey")
MINIO_STORAGE_MEDIA_BUCKET_NAME = os.environ.get("MINIO_STORAGE_MEDIA_BUCKET_NAME", "s3ff-test")
MINIO_STORAGE_AUTO_CREATE_MEDIA_POLICY = "READ_WRITE"
MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = True
MINIO_STORAGE_MEDIA_USE_PRESIGNED = True
