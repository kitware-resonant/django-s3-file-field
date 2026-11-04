from __future__ import annotations

from dataclasses import dataclass
import io
from typing import TYPE_CHECKING, BinaryIO, Self

import requests
from retryable_requests import DEFAULT_RETRY_STRATEGY, RetryableSession
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from ._errors import S3CompletionError, S3FileFieldError, s3_error_code, s3_error_message

if TYPE_CHECKING:
    from collections.abc import Mapping
    from types import TracebackType

    from ._types import (
        CompletedPart,
        CompletionResponse,
        FinalizationResponse,
        InitiationResponse,
        PresignedPart,
    )

# The API's requests are safe to repeat: initiation creates an upload which a lifecycle rule aborts
# if abandoned, and the others are pure functions of their input
_API_RETRIES = DEFAULT_RETRY_STRATEGY.new(
    allowed_methods=set(DEFAULT_RETRY_STRATEGY.allowed_methods or set()) | {"POST"}
)
# Completing is repeated deliberately (see _send_s3_completion); uploading a part is a PUT, which
# the default policy already retries, since it overwrites
_S3_RETRIES = DEFAULT_RETRY_STRATEGY.new(
    allowed_methods=set(DEFAULT_RETRY_STRATEGY.allowed_methods or set()) | {"POST"}
)
# S3 responds to a part once it has received it, and sends whitespace while assembling a
# completion, so this long a silence means a stalled server
_S3_TIMEOUT = (3.05, 60)


@dataclass
class _File:
    name: str
    size: int
    content_type: str
    stream: BinaryIO

    @classmethod
    def from_stream(cls, stream: BinaryIO, name: str, content_type: str) -> _File:
        if not stream.seekable():
            raise ValueError("The file stream must be seekable.")

        stream.seek(0, io.SEEK_END)
        size = stream.tell()
        stream.seek(0, io.SEEK_SET)

        return cls(name=name, size=size, content_type=content_type, stream=stream)


class S3FileFieldClient:
    """A client for uploading files to a Django application's ``S3FileField``."""

    def __init__(self, base_url: str, *, headers: Mapping[str, str] | None = None) -> None:
        """
        Create a client.

        :param base_url: The URL of the upload API, where ``s3_file_field.urls`` is mounted.
        :param headers: Headers for the API's requests, such as ``Authorization``.
        """
        self._api = RetryableSession(base_url=base_url, retry_strategy=_API_RETRIES)
        if headers is not None:
            self._api.headers.update(headers)
        # The object store's requests are authorized by their presigned URLs, so the API's
        # headers must not be sent to it
        self._s3 = RetryableSession(retry_strategy=_S3_RETRIES, timeout=_S3_TIMEOUT)

    def close(self) -> None:
        """Close the client's connections."""
        self._api.close()
        self._s3.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def _initiate_upload(self, file: _File, field_id: str) -> InitiationResponse:
        resp = self._api.post(
            "initiate/",
            json={
                "field": field_id,
                "file_name": file.name,
                "file_size": file.size,
                "content_type": file.content_type,
            },
        )
        resp.raise_for_status()
        initiation: InitiationResponse = resp.json()
        return initiation

    def _upload_part(self, part_bytes: bytes, presigned_part: PresignedPart) -> CompletedPart:
        resp = self._s3.put(presigned_part["url"], data=part_bytes)
        resp.raise_for_status()

        etag = resp.headers.get("ETag")
        if etag is None:
            raise S3FileFieldError("ETag header missing from response.", status=resp.status_code)

        return {
            "part_number": presigned_part["part_number"],
            "etag": etag,
        }

    def _upload_parts(
        self, file: _File, presigned_parts: list[PresignedPart]
    ) -> list[CompletedPart]:
        return [
            self._upload_part(file.stream.read(presigned_part["size"]), presigned_part)
            for presigned_part in presigned_parts
        ]

    def _complete_upload(
        self, initiation: InitiationResponse, completed_parts: list[CompletedPart]
    ) -> None:
        resp = self._api.post(
            "complete/",
            json={
                "upload_token": initiation["upload_token"],
                # Mypy doesn't yet implement PEP 728 Mapping assignability for closed TypedDicts
                # (python/mypy#18176); once it does, this ignore will be flagged as unused
                "parts": completed_parts,  # type: ignore[dict-item]
            },
        )
        resp.raise_for_status()
        completion: CompletionResponse = resp.json()

        self._send_s3_completion(completion)

    @retry(
        retry=retry_if_exception_type(S3CompletionError),
        # Same retry schedule as Boto3's standard mode:
        # https://docs.aws.amazon.com/boto3/latest/guide/retries.html#standard-retry-mode
        stop=stop_after_attempt(3),
        wait=wait_random_exponential(multiplier=2, max=20),
        reraise=True,
    )
    def _send_s3_completion(self, completion: CompletionResponse) -> None:
        # Send no Content-Type, as S3 misinterprets the body under some types.
        response = self._s3.post(completion["url"], data=completion["body"].encode())
        response.raise_for_status()
        # S3 may begin its response with 200, then report an error in the body.
        if error_code := s3_error_code(response.text):
            if error_code == "NoSuchUpload":
                # When an attempt succeeds but its response is lost, the repeat finds the upload
                # gone. In this case, provisionally assume success and continue. Finalization
                # verifies that the object exists, so let it definitively determine success.
                return
            raise S3CompletionError(
                s3_error_message(response.text) or f"Upload failed with {error_code}.",
                status=response.status_code,
            )

    def _finalize(self, upload_token: str) -> str:
        resp = self._api.post(
            "finalize/",
            json={
                "upload_token": upload_token,
            },
        )
        resp.raise_for_status()
        finalization: FinalizationResponse = resp.json()
        return finalization["field_value"]

    def upload_file(
        self, *, file_stream: BinaryIO, file_name: str, file_content_type: str, field_id: str
    ) -> str:
        """
        Upload a file, returning the value to submit for the field.

        :param file_stream: The file's content, open in binary mode and seekable.
        :param file_name: The file's name.
        :param file_content_type: The file's MIME type.
        :param field_id: The field to upload to, as ``"<app>.<model>.<field>"``.
        :raises S3FileFieldError: If the upload fails, with the underlying exception as its cause.
        """
        file = _File.from_stream(file_stream, file_name, file_content_type)
        try:
            initiation = self._initiate_upload(file, field_id)
            completed_parts = self._upload_parts(file, initiation["parts"])
            self._complete_upload(initiation, completed_parts)
            return self._finalize(initiation["upload_token"])
        except requests.RequestException as error:
            raise S3FileFieldError.from_request_exception(error) from error
