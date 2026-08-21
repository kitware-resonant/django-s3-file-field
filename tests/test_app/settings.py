from __future__ import annotations

import os

import django

ROOT_URLCONF = "test_app.urls"
SECRET_KEY = "insecure-secret"
SITE_ID = 1

INSTALLED_APPS = [
    "test_app",
    "s3_file_field",
    "rest_framework",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.humanize",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
]

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "static/"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

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
