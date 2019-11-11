from rest_framework import serializers

from core.models import Blob


class BlobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blob
        fields = ['id', 'created', 'creator', 'resource']
