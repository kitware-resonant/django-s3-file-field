from __future__ import annotations

import sys

if sys.version_info >= (3, 15):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


class PartInitialization(TypedDict, closed=True):
    part_number: int
    size: int
    upload_url: str


class MultipartInitialization(TypedDict, closed=True):
    upload_signature: str
    parts: list[PartInitialization]


class TransferredPart(TypedDict, closed=True):
    part_number: int
    size: int
    etag: str


class UploadCompletion(TypedDict, closed=True):
    complete_url: str
    body: str


class Finalization(TypedDict, closed=True):
    field_value: str
