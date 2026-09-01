from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, override

from django.core import signing
from django.http import JsonResponse
from pydantic import ValidationError
from rest_framework import serializers
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser
from rest_framework.response import Response

from . import _multipart, _registry
from ._multipart import (
    ObjectNotFoundError,
    PresignedUploadCompletion,
    TransferredPart,
    TransferredParts,
    UploadTooLargeError,
)
from ._pydantic_utils import PydanticEncoder
from ._schemas import (
    PartInitializationModel,
    UploadInitializationRequestModel,
    UploadInitializationResponseModel,
    UploadSignatureModel,
)

if TYPE_CHECKING:
    from django.http.response import HttpResponseBase
    from rest_framework.request import Request


class TransferredPartRequestSerializer(serializers.Serializer[TransferredPart]):
    part_number = serializers.IntegerField(min_value=1)
    size = serializers.IntegerField(min_value=1)
    etag = serializers.CharField()


class UploadCompletionRequestSerializer(serializers.Serializer[TransferredParts]):
    upload_signature = serializers.CharField(trim_whitespace=False)
    upload_id = serializers.CharField()
    parts = TransferredPartRequestSerializer(many=True, allow_empty=False)

    @override
    def create(self, validated_data: dict[str, Any]) -> TransferredParts:
        parts = [
            TransferredPart(**part)
            for part in sorted(validated_data.pop("parts"), key=lambda part: part["part_number"])
        ]
        upload_signature = signing.loads(validated_data["upload_signature"], salt="s3_file_field")
        object_key = upload_signature["object_key"]
        upload_id = validated_data["upload_id"]
        return TransferredParts(parts=parts, object_key=object_key, upload_id=upload_id)


class UploadCompletionResponseSerializer(serializers.Serializer[PresignedUploadCompletion]):
    complete_url = serializers.URLField()
    body = serializers.CharField(trim_whitespace=False)


@dataclass
class FinalizationRequest:
    upload_signature: str


class FinalizationRequestSerializer(serializers.Serializer[FinalizationRequest]):
    upload_signature = serializers.CharField(trim_whitespace=False)

    @override
    def create(self, validated_data: dict[str, Any]) -> FinalizationRequest:
        return FinalizationRequest(**validated_data)


@dataclass
class FinalizationResponse:
    field_value: str


class FinalizationResponseSerializer(serializers.Serializer[FinalizationResponse]):
    field_value = serializers.CharField(trim_whitespace=False)


@api_view(["POST"])
def upload_initialize(request: Request) -> JsonResponse:
    try:
        upload_request = UploadInitializationRequestModel.model_validate_json(request.body)
    except ValidationError as e:
        return JsonResponse(
            {"detail": e.errors(include_url=False, include_context=False, include_input=False)},
            status=400,
            encoder=PydanticEncoder,
        )

    field = upload_request.field_id
    # TODO: The first argument to generate_filename() is an instance of the model.
    # We do not and will never have an instance of the model during field upload.
    # Maybe we need a different generate method/upload_to with a different signature?
    object_key = field.generate_filename(None, upload_request.file_name)

    try:
        initialization = _multipart.MultipartManager.from_storage(field.storage).initialize_upload(
            object_key,
            upload_request.file_size,
            upload_request.content_type,
        )
    except UploadTooLargeError:
        return JsonResponse({"detail": "Upload size is too large."}, status=400)

    # signals.s3_file_field_upload_prepare.send(
    #     sender=upload_prepare, name=name, object_key=object_key
    # )

    return JsonResponse(
        UploadInitializationResponseModel(
            object_key=initialization.object_key,
            upload_id=initialization.upload_id,
            parts=[
                PartInitializationModel(**dataclasses.asdict(part)) for part in initialization.parts
            ],
            # TODO: any risks to model_construct?
            upload_signature=UploadSignatureModel.model_construct(
                field_id=field, object_key=initialization.object_key
            ),
        ).model_dump(),
        encoder=PydanticEncoder,
    )


@api_view(["POST"])
@parser_classes([JSONParser])
def upload_complete(request: Request) -> HttpResponseBase:
    request_serializer = UploadCompletionRequestSerializer(data=request.data)
    request_serializer.is_valid(raise_exception=True)
    transferred_parts: TransferredParts = request_serializer.save()

    upload_signature = signing.loads(
        request_serializer.validated_data["upload_signature"], salt="s3_file_field"
    )
    field = _registry.get_field(upload_signature["field_id"])

    # check if upload_prepare signed this less than max age ago
    # tsigner = TimestampSigner()
    # if object_key != tsigner.unsign(
    #     upload_sig, max_age=int(MultipartManager._url_expiration.total_seconds())
    # ):
    #     raise BadSignature()

    completed_upload = _multipart.MultipartManager.from_storage(field.storage).complete_upload(
        transferred_parts
    )

    # signals.s3_file_field_upload_finalize.send(
    #     sender=multipart_upload_finalize, name=name, object_key=object_key
    # )

    response_serializer = UploadCompletionResponseSerializer(completed_upload)
    return Response(response_serializer.data)


@api_view(["POST"])
@parser_classes([JSONParser])
def finalize(request: Request) -> HttpResponseBase:
    request_serializer = FinalizationRequestSerializer(data=request.data)
    request_serializer.is_valid(raise_exception=True)
    finalization_request: FinalizationRequest = request_serializer.save()

    upload_signature = signing.loads(finalization_request.upload_signature, salt="s3_file_field")
    field_id = upload_signature["field_id"]
    object_key = upload_signature["object_key"]

    field = _registry.get_field(field_id)

    # get_object_size implicitly verifies that the object exists.
    # We don't want to distribute the field value if the upload did not complete.
    try:
        size = _multipart.MultipartManager.from_storage(field.storage).get_object_size(object_key)
    except ObjectNotFoundError:
        return Response("Object not found", status=400)

    field_value = signing.dumps(
        {
            "object_key": object_key,
            "file_size": size,
        }
    )

    response_serializer = FinalizationResponseSerializer(
        FinalizationResponse(field_value=field_value)
    )
    return Response(response_serializer.data)
