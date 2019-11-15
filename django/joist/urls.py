from django.contrib import admin
from django.urls import include, path
from rest_framework import routers
from rest_framework.authtoken import views as authviews

from core import views

router = routers.DefaultRouter()
router.register(r'blob', views.BlobViewSet)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/file-upload-url/', views.file_upload_url),
    path('api/finalize-upload/', views.finalize_upload),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api/auth/', authviews.obtain_auth_token),
]
