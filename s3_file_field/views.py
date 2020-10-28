from typing import Dict

from django.core import signing
from django.http.response import HttpResponseBase
from rest_framework import serializers
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.response import Response

from . import _multipart, _registry
from ._multipart import PartFinalization, UploadFinalization


class UploadInitializationRequestSerializer(serializers.Serializer):
    field_id = serializers.CharField()
    file_name = serializers.CharField(trim_whitespace=False)
    file_size = serializers.IntegerField(min_value=1)
    # part_size = serializers.IntegerField(min_value=1)


class PartInitializationResponseSerializer(serializers.Serializer):
    part_number = serializers.IntegerField(min_value=1)
    size = serializers.IntegerField(min_value=1)
    upload_url = serializers.URLField()


class UploadInitializationResponseSerializer(serializers.Serializer):
    object_key = serializers.CharField(trim_whitespace=False)
    upload_id = serializers.CharField()
    parts = PartInitializationResponseSerializer(many=True, allow_empty=False)


class PartFinalizationRequestSerializer(serializers.Serializer):
    part_number = serializers.IntegerField(min_value=1)
    size = serializers.IntegerField(min_value=1)
    etag = serializers.CharField()

    def create(self, validated_data) -> PartFinalization:
        return PartFinalization(**validated_data)


class UploadFinalizationRequestSerializer(serializers.Serializer):
    field_id = serializers.CharField()
    object_key = serializers.CharField(trim_whitespace=False)
    upload_id = serializers.CharField()
    parts = PartFinalizationRequestSerializer(many=True, allow_empty=False)

    def create(self, validated_data) -> UploadFinalization:
        parts = [
            PartFinalization(**part)
            for part in sorted(validated_data.pop('parts'), key=lambda part: part['part_number'])
        ]
        del validated_data['field_id']
        return UploadFinalization(parts=parts, **validated_data)


class UploadFinalizationResponseSerializer(serializers.Serializer):
    field_value = serializers.CharField(trim_whitespace=False)


# @authentication_classes([TokenAuthentication])
# @permission_classes([IsAuthenticated])
@api_view(['POST'])
@parser_classes([JSONParser])
def upload_initialize(request: Request) -> HttpResponseBase:
    request_serializer = UploadInitializationRequestSerializer(data=request.data)
    request_serializer.is_valid(raise_exception=True)
    upload_request: Dict = request_serializer.validated_data
    field = _registry.get_field(upload_request['field_id'])

    # TODO The first argument to generate_filename() is an instance of the model.
    # We do not and will never have an instance of the model during field upload.
    # Maybe we need a different generate method/upload_to with a different signature?
    object_key = field.generate_filename(None, upload_request['file_name'])

    initialization = _multipart.MultipartManager.from_storage(field.storage).initialize_upload(
        object_key, upload_request['file_size']
    )

    # signals.s3_file_field_upload_prepare.send(
    #     sender=upload_prepare, name=name, object_key=object_key
    # )

    # signer = TimestampSigner()
    # sig = signer.sign(object_key)

    response_serializer = UploadInitializationResponseSerializer(initialization)
    return Response(response_serializer.data)


# @authentication_classes([TokenAuthentication])
# @permission_classes([IsAuthenticated])
@api_view(['POST'])
@parser_classes([JSONParser])
def upload_finalize(request: Request) -> HttpResponseBase:
    request_serializer = UploadFinalizationRequestSerializer(data=request.data)
    request_serializer.is_valid(raise_exception=True)
    field = _registry.get_field(request_serializer.validated_data['field_id'])
    finalization: UploadFinalization = request_serializer.save()

    # check if upload_prepare signed this less than max age ago
    # tsigner = TimestampSigner()
    # if object_key != tsigner.unsign(
    #     upload_sig, max_age=int(MultipartManager._url_expiration.total_seconds())
    # ):
    #     raise BadSignature()

    _multipart.MultipartManager.from_storage(field.storage).finalize_upload(finalization)

    # signals.s3_file_field_upload_finalize.send(
    #     sender=multipart_upload_finalize, name=name, object_key=object_key
    # )

    field_value = signing.dumps(
        {
            'object_key': finalization.object_key,
            'file_size': sum(part.size for part in finalization.parts),
        }
    )

    response_serializer = UploadFinalizationResponseSerializer(
        {
            'field_value': field_value,
        }
    )
    return Response(response_serializer.data)
