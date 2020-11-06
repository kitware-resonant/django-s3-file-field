from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from rest_framework import routers
from s3ff_example.core import rest, views

router = routers.DefaultRouter()
router.register('resources', rest.ResourceViewSet, basename='api')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/s3ff/', include('s3_file_field.urls')),
    path('', RedirectView.as_view(pattern_name='resource-list')),
    path('resources/', views.ResourceList.as_view(), name='resource-list'),
    path('resources/create/', views.ResourceCreate.as_view(), name='resource-create'),
    path('resources/<int:pk>/', views.ResourceUpdate.as_view(), name='resource-update'),
    path('resources/<int:pk>/delete/', views.ResourceDelete.as_view(), name='resource-delete'),
    path('api/', include(router.urls)),
]
