from __future__ import annotations

from rest_framework import serializers, viewsets

from .models import Resource


class ResourceSerializer(serializers.ModelSerializer[Resource]):
    class Meta:
        model = Resource
        fields = "__all__"


class ResourceViewSet(viewsets.ModelViewSet[Resource]):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
