from django.contrib import admin
from django.urls import include, path
from rest_framework import routers
from rest_framework.authtoken import views as authviews

from .views import BlobViewSet, DetailView, IndexView, new_blob, save_blob

router = routers.DefaultRouter()
router.register(r'blob', BlobViewSet)


urlpatterns = [
    path('blob/', IndexView.as_view(), name='index'),
    path('blob/new/', new_blob, name='new'),
    path('blob/<int:pk>/', DetailView.as_view(), name='detail'),
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/save-blob/', save_blob),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api/auth/', authviews.obtain_auth_token),
    path('api/joist/', include('joist.urls')),
]
