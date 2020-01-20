from typing import Any, List

from django.urls import path

from .settings import _JOIST_STORAGE_PROVIDER
from .views import upload_finalize, upload_prepare

urlpatterns = (
    []
    if not _JOIST_STORAGE_PROVIDER
    else [path('upload-prepare/', upload_prepare), path('upload-finalize/', upload_finalize)]
)


def add_url_patterns(patterns: List[Any], prefix='api/joist'):
    patterns.append(path(prefix, urlpatterns))
