from __future__ import annotations

from typing import TypedDict


class PartInitialization(TypedDict):
    part_number: int
    size: int
    upload_url: str


class MultipartInitialization(TypedDict):
    object_key: str
    upload_id: str
    parts: list[PartInitialization]
    upload_signature: str


class TransferredPart(TypedDict):
    part_number: int
    size: int
    etag: str


class UploadCompletion(TypedDict):
    complete_url: str
    body: str


class Finalization(TypedDict):
    field_value: str
