from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import JsonResponse
from pydantic import ValidationError
from rest_framework.decorators import api_view

from . import _multipart
from ._multipart import (
    ObjectNotFoundError,
    TransferredPart,
    TransferredParts,
    UploadTooLargeError,
)
from ._pydantic_utils import PydanticEncoder
from ._schemas import (
    FieldValueModel,
    PartInitializationModel,
    UploadCompletionRequestModel,
    UploadCompletionResponseModel,
    UploadFinalizationRequestModel,
    UploadFinalizationResponseModel,
    UploadInitializationRequestModel,
    UploadInitializationResponseModel,
    UploadSignatureModel,
)

if TYPE_CHECKING:
    from rest_framework.request import Request


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
            # TODO: any risks to model_construct?
            upload_signature=UploadSignatureModel.model_construct(
                field_id=field,
                upload_id=initialization.upload_id,
                object_key=initialization.object_key,
            ),
            parts=[
                PartInitializationModel(
                    part_number=part.part_number,
                    size=part.size,
                    upload_url=part.upload_url,
                )
                for part in initialization.parts
            ],
        ).model_dump(),
        encoder=PydanticEncoder,
    )


@api_view(["POST"])
def upload_complete(request: Request) -> JsonResponse:
    try:
        upload_request = UploadCompletionRequestModel.model_validate_json(request.body)
    except ValidationError as e:
        return JsonResponse(
            {"detail": e.errors(include_url=False, include_context=False, include_input=False)},
            status=400,
            encoder=PydanticEncoder,
        )

    field = upload_request.upload_signature.field_id
    completed_upload = _multipart.MultipartManager.from_storage(field.storage).complete_upload(
        TransferredParts(
            upload_id=upload_request.upload_signature.upload_id,
            object_key=upload_request.upload_signature.object_key,
            parts=[
                TransferredPart(
                    part_number=part.part_number,
                    etag=part.etag,
                )
                for part in upload_request.parts
            ],
        )
    )

    # signals.s3_file_field_upload_finalize.send(
    #     sender=multipart_upload_finalize, name=name, object_key=object_key
    # )

    return JsonResponse(
        UploadCompletionResponseModel(
            complete_url=completed_upload.complete_url,
            body=completed_upload.body,
        ).model_dump(),
        encoder=PydanticEncoder,
    )


@api_view(["POST"])
def finalize(request: Request) -> JsonResponse:
    try:
        upload_request = UploadFinalizationRequestModel.model_validate_json(request.body)
    except ValidationError as e:
        return JsonResponse(
            {"detail": e.errors(include_url=False, include_context=False, include_input=False)},
            status=400,
            encoder=PydanticEncoder,
        )

    field = upload_request.upload_signature.field_id
    object_key = upload_request.upload_signature.object_key

    # get_object_size implicitly verifies that the object exists.
    # We don't want to distribute the field value if the upload did not complete.
    try:
        size = _multipart.MultipartManager.from_storage(field.storage).get_object_size(object_key)
    except ObjectNotFoundError:
        return JsonResponse(
            {"detail": "The upload was not completed or the object has been deleted."}, status=400
        )

    return JsonResponse(
        UploadFinalizationResponseModel(
            field_value=FieldValueModel.model_construct(
                object_key=object_key,
                file_size=size,
            ),
        ).model_dump(),
        encoder=PydanticEncoder,
    )
