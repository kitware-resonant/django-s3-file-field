from typing import List

from django.urls import path

from .configuration import StorageProvider
from .settings import _S3FF_STORAGE_PROVIDER
from .views import upload_finalize, upload_prepare

app_name = 's3_file_field'
urlpatterns: List = []

if _S3FF_STORAGE_PROVIDER != StorageProvider.UNSUPPORTED:
    urlpatterns += [
        path('upload-prepare/', upload_prepare, name='upload-prepare'),
        path('upload-finalize/', upload_finalize, name='upload-finalize'),
    ]
