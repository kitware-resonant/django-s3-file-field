from __future__ import annotations

import sys

if sys.version_info >= (3, 15):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict


class PresignedPart(TypedDict, closed=True):
    part_number: int
    size: int
    url: str


class InitiationResponse(TypedDict, closed=True):
    upload_token: str
    parts: list[PresignedPart]


class CompletedPart(TypedDict, closed=True):
    part_number: int
    etag: str


class CompletionResponse(TypedDict, closed=True):
    url: str
    body: str


class FinalizationResponse(TypedDict, closed=True):
    field_value: str
