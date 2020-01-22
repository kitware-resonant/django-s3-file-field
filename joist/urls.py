from typing import List

from django.urls import path

from .configuration import StorageProvider
from .settings import _JOIST_STORAGE_PROVIDER
from .views import upload_finalize, upload_prepare

urlpatterns: List = []

if _JOIST_STORAGE_PROVIDER != StorageProvider.UNSUPPORTED:
    urlpatterns += [
        path('upload-prepare/', upload_prepare),
        path('upload-finalize/', upload_finalize),
    ]
