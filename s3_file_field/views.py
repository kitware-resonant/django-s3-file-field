import uuid

from django.core.files.storage import default_storage
from django.http.response import HttpResponseBase
from rest_framework import serializers
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.response import Response

from . import _multipart, constants
from ._multipart import MultipartFinalization, PartFinalization


class PartInitializationSerializer(serializers.Serializer):
    part_number = serializers.IntegerField(min_value=1)
    size = serializers.IntegerField(min_value=1)
    upload_url = serializers.URLField()


class MultipartInitializationSerializer(serializers.Serializer):
    object_key = serializers.CharField(trim_whitespace=False)
    upload_id = serializers.CharField()
    parts = PartInitializationSerializer(many=True, allow_empty=False)


class PartFinalizationSerializer(serializers.Serializer):
    part_number = serializers.IntegerField(min_value=1)
    size = serializers.IntegerField(min_value=1)
    etag = serializers.CharField()

    def create(self, validated_data) -> PartFinalization:
        return PartFinalization(**validated_data)


class MultipartFinalizationSerializer(serializers.Serializer):
    object_key = serializers.CharField(trim_whitespace=False)
    upload_id = serializers.CharField()
    parts = PartFinalizationSerializer(many=True, allow_empty=False)

    def create(self, validated_data) -> MultipartFinalization:
        parts = [
            PartFinalization(**part)
            for part in sorted(validated_data.pop('parts'), key=lambda part: part['part_number'])
        ]
        return MultipartFinalization(parts=parts, **validated_data)


# @authentication_classes([TokenAuthentication])
# @permission_classes([IsAuthenticated])
@api_view(['POST'])
@parser_classes([JSONParser])
def multipart_upload_prepare(request: Request) -> HttpResponseBase:
    name = request.data['name']
    content_length = request.data['content_length']
    max_part_length = request.data.get('max_part_length')

    object_key = str(constants.S3FF_UPLOAD_PREFIX / str(uuid.uuid4()) / name)

    multipart_initialization = _multipart.MultipartManager.from_storage(
        default_storage
    ).initialize_upload(object_key, content_length, max_part_length)

    # signals.s3_file_field_upload_prepare.send(
    #     sender=upload_prepare, name=name, object_key=object_key
    # )

    # signer = TimestampSigner()
    # sig = signer.sign(object_key)

    serializer = MultipartInitializationSerializer(multipart_initialization)
    return Response(serializer.data)


# @authentication_classes([TokenAuthentication])
# @permission_classes([IsAuthenticated])
@api_view(['POST'])
@parser_classes([JSONParser])
def multipart_upload_finalize(request: Request) -> HttpResponseBase:
    serializer = MultipartFinalizationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    finalization = serializer.save()

    # check if upload_prepare signed this less than max age ago
    # tsigner = TimestampSigner()
    # if object_key != tsigner.unsign(upload_sig, max_age=constants.S3FF_UPLOAD_DURATION):
    #     raise BadSignature()

    _multipart.MultipartManager.from_storage(default_storage).finalize_upload(finalization)

    # signals.s3_file_field_upload_finalize.send(
    #     sender=multipart_upload_finalize, name=name, object_key=object_key
    # )

    # signer = Signer()
    # sig = signer.sign(object_key)

    return Response(status=201)
