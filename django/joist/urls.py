from django.contrib import admin
from django.urls import include, path
from rest_framework import routers
from rest_framework.authtoken import views as authviews

from core import views as cviews
from .views import BlobViewSet, save_blob

router = routers.DefaultRouter()
router.register(r'blob', BlobViewSet)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/save-blob/', save_blob),

    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api/auth/', authviews.obtain_auth_token),

    path('api/joist/file-upload-url/', cviews.file_upload_url),
    path('api/joistfinalize-upload/', cviews.finalize_upload),
]
