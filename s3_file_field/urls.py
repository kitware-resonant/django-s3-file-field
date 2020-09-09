from django.urls import path

from .views import upload_finalize, upload_initialize

app_name = 's3_file_field'

urlpatterns = [
    path('upload-initialize/', upload_initialize, name='upload-initialize'),
    path(
        'upload-finalize/',
        upload_finalize,
        name='upload-finalize',
    ),
]
