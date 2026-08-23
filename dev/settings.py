from __future__ import annotations

import os
from pathlib import Path

import django_stubs_ext

django_stubs_ext.monkeypatch()

BASE_DIR = Path(__file__).resolve(strict=True).parent

ROOT_URLCONF = "urls"
SECRET_KEY = "insecure-secret"
SITE_ID = 1

DEBUG = True
INTERNAL_IPS = ["127.0.0.1"]

INSTALLED_APPS = [
    "s3ff_dev",
    "s3_file_field",
    "debug_toolbar",
    "django_browser_reload",
    "django_extensions",
    "rest_framework",
    "rest_framework.authtoken",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.humanize",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
TIME_ZONE = "UTC"

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

STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
if "AWS_ACCESS_KEY_ID" in os.environ:
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
    }
    AWS_S3_REGION_NAME = os.environ.get("AWS_DEFAULT_REGION", "us-east1")
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_SIGNATURE_VERSION = "s3v4"
else:
    STORAGES["default"] = {
        "BACKEND": "minio_storage.storage.MinioMediaStorage",
    }
    MINIO_STORAGE_ENDPOINT = "localhost:9000"
    MINIO_STORAGE_USE_HTTPS = False
    MINIO_STORAGE_ACCESS_KEY = "minioAccessKey"
    MINIO_STORAGE_SECRET_KEY = "minioSecretKey"
    MINIO_STORAGE_MEDIA_BUCKET_NAME = "s3ff-dev"
    MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = True
    MINIO_STORAGE_AUTO_CREATE_MEDIA_POLICY = "READ_WRITE"
    MINIO_STORAGE_MEDIA_USE_PRESIGNED = True
