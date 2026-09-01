from __future__ import annotations

import re
from typing import ClassVar


class Fuzzy:
    pattern: re.Pattern[str]

    # Hashing cannot be made consistent with this __eq__, so disable it
    __hash__: ClassVar[None] = None  # type: ignore[assignment]

    def __init__(self, pattern: str | re.Pattern[str]) -> None:
        self.pattern: re.Pattern[str] = (
            pattern if isinstance(pattern, re.Pattern) else re.compile(pattern)
        )

    def __eq__(self, other: object) -> bool:
        return isinstance(other, str) and self.pattern.search(other) is not None

    def __str__(self) -> str:
        return self.pattern.pattern

    def __repr__(self) -> str:
        return repr(self.pattern.pattern)


# This only validates the beginning of a URL, which is good enough
FUZZY_URL = Fuzzy(r"^http[s]?://[a-zA-Z0-9_-]+(?::[0-9]+)?/?")

# Different versions of MinIO may use the following upload ID formats:
# * A UUID
# * A Base64-encoded string of two dot-delimited UUIDs
# * A Base64-encoded (URL-safe and unpadded) string of two dot-delimited UUIDs
# AWS uses a random sequence of characters.
# So, just allow any sequence of characters.
FUZZY_UPLOAD_ID = Fuzzy(r"^[A-Za-z0-9+/=-]+$")


class FuzzyPositiveInt:
    # Hashing cannot be made consistent with this __eq__, so disable it
    __hash__: ClassVar[None] = None  # type: ignore[assignment]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, int) and other > 0

    def __repr__(self) -> str:
        return "<any positive int>"


FUZZY_POSITIVE_INT = FuzzyPositiveInt()
