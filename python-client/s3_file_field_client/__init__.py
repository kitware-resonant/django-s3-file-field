from __future__ import annotations

from dataclasses import dataclass
import io
from typing import TYPE_CHECKING, BinaryIO, ClassVar

import requests

if TYPE_CHECKING:
    from ._types import (
        Finalization,
        MultipartInitialization,
        PartInitialization,
        TransferredPart,
        UploadCompletion,
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

    def _initialize_upload(self, file: _File, field_id: str) -> MultipartInitialization:
        resp = self.api_session.post(
            f"{self.base_url}/upload-initialize/",
            json={
                "field_id": field_id,
                "file_name": file.name,
                "file_size": file.size,
                "content_type": file.content_type,
            },
            timeout=self.request_timeout,
        )
        resp.raise_for_status()
        multipart_info: MultipartInitialization = resp.json()
        return multipart_info

    def _upload_part(
        self, part_bytes: bytes, part_initialization: PartInitialization
    ) -> TransferredPart:
        resp = requests.put(
            part_initialization["upload_url"], data=part_bytes, timeout=self.request_timeout
        )
        resp.raise_for_status()

        etag = resp.headers["ETag"]

        return {
            "part_number": part_initialization["part_number"],
            "etag": etag,
        }

    def _upload_parts(
        self, file: _File, part_initializations: list[PartInitialization]
    ) -> list[TransferredPart]:
        return [
            self._upload_part(file.stream.read(part_initialization["size"]), part_initialization)
            for part_initialization in part_initializations
        ]

    def _complete_upload(
        self, multipart_info: MultipartInitialization, upload_infos: list[TransferredPart]
    ) -> None:
        resp = self.api_session.post(
            f"{self.base_url}/upload-complete/",
            json={
                "upload_signature": multipart_info["upload_signature"],
                # Mypy doesn't yet implement PEP 728 Mapping assignability for closed TypedDicts
                # (python/mypy#18176); once it does, this ignore will be flagged as unused
                "parts": upload_infos,  # type: ignore[dict-item]
            },
            timeout=self.request_timeout,
        )
        resp.raise_for_status()
        completion_data: UploadCompletion = resp.json()

        complete_resp = requests.post(
            completion_data["complete_url"],
            data=completion_data["body"],
            timeout=self.request_timeout,
        )
        complete_resp.raise_for_status()

    def _finalize(self, multipart_info: MultipartInitialization) -> str:
        resp = self.api_session.post(
            f"{self.base_url}/finalize/",
            json={
                "upload_signature": multipart_info["upload_signature"],
            },
            timeout=self.request_timeout,
        )
        resp.raise_for_status()
        finalization: Finalization = resp.json()
        return finalization["field_value"]

    def upload_file(
        self, *, file_stream: BinaryIO, file_name: str, file_content_type: str, field_id: str
    ) -> str:
        file = _File.from_stream(file_stream, file_name, file_content_type)
        multipart_info = self._initialize_upload(file, field_id)
        upload_infos = self._upload_parts(file, multipart_info["parts"])
        self._complete_upload(multipart_info, upload_infos)
        return self._finalize(multipart_info)
