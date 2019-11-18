from typing import Any, List

from django.urls import path

from .views import finalize_upload, prepare_upload


def add_url_patterns(urlpatterns: List[Any], prefix='api/joist'):
    urlpatterns.extend(
        [
            path(f'{prefix}/prepare-upload/', prepare_upload),
            path(f'{prefix}/finalize-upload/', finalize_upload),
        ]
    )
