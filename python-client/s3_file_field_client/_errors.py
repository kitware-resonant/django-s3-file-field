from __future__ import annotations

import re
from typing import Self

import requests

# S3 describes an error in XML, like:
#   <Error>
#     <Code>InvalidPart</Code>
#     <Message>One or more of the specified parts could not be found.</Message>
#     <RequestId>4442587FB7D0A2F9</RequestId>
#   </Error>
# Anchor the patterns at the start, to avoid possible quadratic backtracking on
# technically-untrusted input.
_S3_ERROR_CODE = re.compile(r"\A\s*(?:<\?xml[^>]*>\s*)?<Error>.*?<Code>([^<]*)</Code>", re.DOTALL)
_S3_ERROR_MESSAGE = re.compile(
    r"\A\s*(?:<\?xml[^>]*>\s*)?<Error>.*?<Message>([^<]*)</Message>", re.DOTALL
)


def s3_error_code(body: str) -> str | None:
    """Return the code of an S3 error, if the body of a response describes one."""
    match = _S3_ERROR_CODE.match(body)
    return match[1] if match else None


def s3_error_message(body: str) -> str | None:
    """Return the message of an S3 error, if the body of a response describes one."""
    match = _S3_ERROR_MESSAGE.match(body)
    return match[1] if match else None


def api_error_detail(response: requests.Response) -> str | None:
    """Return the explanation in the API's JSON error body, when it gives one.

    The API describes an error in JSON, like:
      {"detail": "Upload size is too large."}
    or, for invalid input, with a list of validation errors, the first of which explains it:
      {"detail": [{"type": "missing", "loc": ["file_name"], "msg": "Field required"}]}
    """
    try:
        data = response.json()
    except requests.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    detail = data.get("detail")
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list) and detail and isinstance(detail[0], dict):
        msg = detail[0].get("msg")
        if isinstance(msg, str):
            return msg
    return None


class S3FileFieldError(Exception):
    """The failure of an upload.

    The message is suitable for display: the server's explanation, when it gave one, or else a
    description of the failure. The cause (``__cause__``) is the underlying ``requests``
    exception, when there is one, for diagnosis.
    """

    status: int | None
    """The HTTP status of the response, if one was received."""
    detail: str | None
    """The server's explanation of the failure, if it gave one."""

    def __init__(
        self, message: str, *, status: int | None = None, detail: str | None = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.detail = detail

    @classmethod
    def from_request_exception(cls, error: requests.RequestException) -> Self:
        """Describe the failure of a request made by ``requests``."""
        response = error.response
        if response is not None:
            status = response.status_code
            # The API explains an error in JSON; S3 in XML
            detail = api_error_detail(response) or s3_error_message(response.text)
            return cls(detail or f"Upload failed with HTTP {status}.", status=status, detail=detail)
        if isinstance(error, requests.Timeout):
            return cls("Upload timed out.")
        if isinstance(error, requests.ConnectionError):
            return cls("Upload failed with a network error.")
        return cls("Upload failed.")
