from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import SuspiciousOperation
from django.http import JsonResponse
from pydantic import ValidationError
from rest_framework.decorators import api_view

from . import _multipart, _schemas
from ._multipart import ObjectNotFoundError, UploadTooLargeError
from ._pydantic_utils import PydanticEncoder

if TYPE_CHECKING:
    from rest_framework.request import Request


@api_view(["POST"])
def initiate(request: Request) -> JsonResponse:
    try:
        initiation_request = _schemas.InitiationRequest.model_validate_json(request.body)
    except ValidationError as e:
        return JsonResponse(
            {"detail": e.errors(include_url=False, include_context=False, include_input=False)},
            status=400,
            encoder=PydanticEncoder,
        )

    # TODO: The first argument to generate_filename() is an instance of the model.
    # We do not and will never have an instance of the model during field upload.
    # Maybe we need a different generate method/upload_to with a different signature?
    object_key = initiation_request.field.generate_filename(None, initiation_request.file_name)

    multipart_manager = _multipart.MultipartManager.from_storage(initiation_request.field.storage)
    try:
        presigned_upload = multipart_manager.initiate_upload(
            object_key,
            initiation_request.file_size,
            initiation_request.content_type,
        )
    except UploadTooLargeError:
        return JsonResponse({"detail": "Upload size is too large."}, status=400)

    return JsonResponse(
        _schemas.InitiationResponse(
            # TODO: any risks to model_construct?
            upload_token=_schemas.UploadToken.model_construct(
                field=initiation_request.field,
                upload_id=presigned_upload.upload_id,
                object_key=presigned_upload.object_key,
            ),
            parts=[
                _schemas.PresignedPart(
                    part_number=part.part_number,
                    size=part.size,
                    url=part.url,
                )
                for part in presigned_upload.parts
            ],
        ).model_dump(),
        encoder=PydanticEncoder,
    )


@api_view(["POST"])
def complete(request: Request) -> JsonResponse:
    try:
        completion_request = _schemas.CompletionRequest.model_validate_json(request.body)
    except ValidationError as e:
        return JsonResponse(
            {"detail": e.errors(include_url=False, include_context=False, include_input=False)},
            status=400,
            encoder=PydanticEncoder,
        )

    multipart_manager = _multipart.MultipartManager.from_storage(
        completion_request.upload_token.field.storage
    )
    presigned_completion = multipart_manager.complete_upload(
        upload_id=completion_request.upload_token.upload_id,
        object_key=completion_request.upload_token.object_key,
        parts=[
            _multipart.CompletedPart(
                part_number=part.part_number,
                etag=part.etag,
            )
            for part in completion_request.parts
        ],
    )

    return JsonResponse(
        _schemas.CompletionResponse(
            url=presigned_completion.url,
            body=presigned_completion.body,
        ).model_dump(),
        encoder=PydanticEncoder,
    )


@api_view(["POST"])
def finalize(request: Request) -> JsonResponse:
    try:
        finalization_request = _schemas.FinalizationRequest.model_validate_json(request.body)
    except ValidationError as e:
        return JsonResponse(
            {"detail": e.errors(include_url=False, include_context=False, include_input=False)},
            status=400,
            encoder=PydanticEncoder,
        )
    upload_token = finalization_request.upload_token

    multipart_manager = _multipart.MultipartManager.from_storage(upload_token.field.storage)
    try:
        size = multipart_manager.get_object_size(upload_token.object_key)
    except ObjectNotFoundError:
        return JsonResponse(
            {"detail": "The upload was not completed or the object has been deleted."}, status=400
        )
    # Initiation checked the declared size, but the limit may have been lowered mid-upload,
    # and MinIO never enforces the presigned part Content-Length; so re-check the actual size
    max_size = upload_token.field.effective_max_size
    if size > max_size:
        # The object is already fully uploaded, so remove it
        upload_token.field.storage.delete(upload_token.object_key)
        raise SuspiciousOperation(
            f"Uploaded object {upload_token.object_key!r} is {size} bytes, "
            f"exceeding the maximum of {max_size} bytes."
        )

    return JsonResponse(
        _schemas.FinalizationResponse(
            field_value=_schemas.FieldValue.model_construct(
                field=upload_token.field,
                object_key=upload_token.object_key,
                file_size=size,
            ),
        ).model_dump(),
        encoder=PydanticEncoder,
    )
