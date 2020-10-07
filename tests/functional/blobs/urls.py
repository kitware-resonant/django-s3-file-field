from django.urls import include, path

urlpatterns = [
    path('api/joist/', include('s3_file_field.urls')),
]
