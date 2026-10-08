from __future__ import annotations

from rest_framework import serializers

from .models import LimitedResource, MultiResource, OptionalResource, Resource, ValidatedResource


class ResourceSerializer(serializers.ModelSerializer[Resource]):
    class Meta:
        model = Resource
        fields = "__all__"


class OptionalResourceSerializer(serializers.ModelSerializer[OptionalResource]):
    class Meta:
        model = OptionalResource
        fields = "__all__"


class MultiResourceSerializer(serializers.ModelSerializer[MultiResource]):
    class Meta:
        model = MultiResource
        fields = "__all__"


class LimitedResourceSerializer(serializers.ModelSerializer[LimitedResource]):
    class Meta:
        model = LimitedResource
        fields = "__all__"


class ValidatedResourceSerializer(serializers.ModelSerializer[ValidatedResource]):
    class Meta:
        model = ValidatedResource
        fields = "__all__"
