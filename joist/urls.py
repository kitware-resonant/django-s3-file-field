from typing import Any, List

from django.urls import path

from .settings import JOIST_STORAGE_PROVIDER
from .views import upload_finalize, upload_prepare

urlpatterns = (
    []
    if JOIST_STORAGE_PROVIDER == 'unknown'
    else [path('upload-prepare/', upload_prepare), path('upload-finalize/', upload_finalize)]
)


def add_url_patterns(patterns: List[Any], prefix='api/joist'):
    patterns.append(path(prefix, urlpatterns))
