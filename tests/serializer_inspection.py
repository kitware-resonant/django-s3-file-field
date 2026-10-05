from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rest_framework.serializers import Serializer


def field_error_codes(serializer: Serializer[Any], field_name: str) -> list[str | None]:
    """Return the error codes for one field of a validated serializer, in order."""
    return [error.code for error in serializer.errors.get(field_name, [])]
