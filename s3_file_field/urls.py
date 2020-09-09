from typing import List

from django.urls import path

from .constants import S3FF_STORAGE_PROVIDER, StorageProvider
from .views import multipart_upload_finalize, multipart_upload_prepare

app_name = 's3_file_field'
urlpatterns: List = []

if S3FF_STORAGE_PROVIDER != StorageProvider.UNSUPPORTED:
    urlpatterns += [
        path(
            'multipart-upload-prepare/', multipart_upload_prepare, name='multipart-upload-prepare'
        ),
        path(
            'multipart-upload-finalize/',
            multipart_upload_finalize,
            name='multipart-upload-finalize',
        ),
    ]
