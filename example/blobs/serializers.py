from rest_framework import serializers

from .models import Blob


class BlobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blob
        fields = ['id', 'created', 'creator', 'resource']
        read_only_fields = ['id', 'created', 'creator', 'resource']
