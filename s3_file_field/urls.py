from __future__ import annotations

from django.urls import path

from .views import complete, finalize, initiate

app_name = "s3_file_field"

urlpatterns = [
    path("initiate/", initiate, name="initiate"),
    path("complete/", complete, name="complete"),
    path("finalize/", finalize, name="finalize"),
]
