from django.urls import include, path

urlpatterns = [
    # Make this distinct from typical production values, to ensure it works dynamically
    path('api/s3ff_test/', include('s3_file_field.urls')),
]
