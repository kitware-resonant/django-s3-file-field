from django.urls import path

from .views import finalize, upload_complete, upload_initialize

app_name = "s3_file_field"

urlpatterns = [
    path("upload-initialize/", upload_initialize, name="upload-initialize"),
    path(
        "upload-complete/",
        upload_complete,
        name="upload-complete",
    ),
    path("finalize/", finalize, name="finalize"),
]
