from typing import List

from django.urls import path

from .constants import S3FF_STORAGE_PROVIDER, StorageProvider
from .views import upload_finalize, upload_prepare

app_name = 's3_file_field'
urlpatterns: List = []

if S3FF_STORAGE_PROVIDER != StorageProvider.UNSUPPORTED:
    urlpatterns += [
        path('upload-prepare/', upload_prepare, name='upload-prepare'),
        path('upload-finalize/', upload_finalize, name='upload-finalize'),
    ]
