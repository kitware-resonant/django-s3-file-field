from __future__ import annotations

import re


class Fuzzy:
    def __init__(self, pattern: str | re.Pattern) -> None:
        self.pattern: re.Pattern = (
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
