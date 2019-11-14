"""
joist URL Configuration.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))

"""
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
    path('api/file-upload-url/<str:name>', views.file_upload_url),
    path('api/finalize-upload', views.finalize_upload),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api/auth/', authviews.obtain_auth_token),
]
