from __future__ import annotations

from dataclasses import dataclass
import io
from typing import TYPE_CHECKING, BinaryIO, ClassVar

import requests

if TYPE_CHECKING:
    from ._types import (
        CompletedPart,
        CompletionResponse,
        FinalizationResponse,
        InitiationResponse,
        PresignedPart,
    )


@dataclass
class _File:
    name: str
    size: int
    content_type: str
    stream: BinaryIO

    @classmethod
    def from_stream(cls, stream: BinaryIO, name: str, content_type: str) -> _File:
        if not stream.seekable():
            raise RuntimeError("File stream is not seekable.")

        stream.seek(0, io.SEEK_END)
        size = stream.tell()
        stream.seek(0, io.SEEK_SET)

        return cls(name=name, size=size, content_type=content_type, stream=stream)


class S3FileFieldClient:
    request_timeout: ClassVar[int] = 5
    base_url: str
    api_session: requests.Session

    def __init__(self, base_url: str, api_session: requests.Session | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_session = requests.Session() if api_session is None else api_session

    def _initiate_upload(self, file: _File, field_id: str) -> InitiationResponse:
        resp = self.api_session.post(
            f"{self.base_url}/initiate/",
            json={
                "field": field_id,
                "file_name": file.name,
                "file_size": file.size,
                "content_type": file.content_type,
            },
            timeout=self.request_timeout,
        )
        resp.raise_for_status()
        initiation: InitiationResponse = resp.json()
        return initiation

    def _upload_part(self, part_bytes: bytes, presigned_part: PresignedPart) -> CompletedPart:
        resp = requests.put(presigned_part["url"], data=part_bytes, timeout=self.request_timeout)
        resp.raise_for_status()

        etag = resp.headers["ETag"]

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
        resp = self.api_session.post(
            f"{self.base_url}/complete/",
            json={
                "upload_token": initiation["upload_token"],
                # Mypy doesn't yet implement PEP 728 Mapping assignability for closed TypedDicts
                # (python/mypy#18176); once it does, this ignore will be flagged as unused
                "parts": completed_parts,  # type: ignore[dict-item]
            },
            timeout=self.request_timeout,
        )
        resp.raise_for_status()
        completion: CompletionResponse = resp.json()

        complete_resp = requests.post(
            completion["url"],
            data=completion["body"],
            timeout=self.request_timeout,
        )
        complete_resp.raise_for_status()

    def _finalize(self, upload_token: str) -> str:
        resp = self.api_session.post(
            f"{self.base_url}/finalize/",
            json={
                "upload_token": upload_token,
            },
            timeout=self.request_timeout,
        )
        resp.raise_for_status()
        finalization: FinalizationResponse = resp.json()
        return finalization["field_value"]

    def upload_file(
        self, *, file_stream: BinaryIO, file_name: str, file_content_type: str, field_id: str
    ) -> str:
        file = _File.from_stream(file_stream, file_name, file_content_type)
        initiation = self._initiate_upload(file, field_id)
        completed_parts = self._upload_parts(file, initiation["parts"])
        self._complete_upload(initiation, completed_parts)
        return self._finalize(initiation["upload_token"])
