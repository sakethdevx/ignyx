import json
from collections import UserDict
from typing import Any, Optional

from ignyx._core import Request as _RustRequest


class Headers(UserDict):
    """Case-insensitive dictionary for HTTP headers."""

    def __setitem__(self, key: str, item: Any) -> None:
        "Set a header value."
        self.data[key.lower()] = item

    def __getitem__(self, key: str) -> Any:
        "Get a header value."
        return self.data[key.lower()]

    def __contains__(self, key: object) -> bool:
        "Check if a header exists."
        if not isinstance(key, str):
            return False
        return key.lower() in self.data

    def __delitem__(self, key: str) -> None:
        "Delete a header."
        del self.data[key.lower()]

    def get(self, key: str, default: Any = None) -> Any:
        "Get a header value with a default."
        return self.data.get(key.lower(), default)


class Request:
    """
    Python wrapper around the Rust Request object.
    Provides typed, native Python dictionary access to request properties.
    """

    def __init__(self, rust_req: _RustRequest) -> None:
        "Initialize the request wrapper."
        self._rust_req: _RustRequest = rust_req

        # Parse JSON blocks eagerly to native Python dictionaries
        raw_headers = json.loads(rust_req.headers) if isinstance(rust_req.headers, str) else {}
        self.headers: Headers = Headers(raw_headers)
        self.query_params: dict[str, Any] = (
            json.loads(rust_req.query_params) if isinstance(rust_req.query_params, str) else {}
        )
        self.path_params: dict[str, Any] = (
            json.loads(rust_req.path_params) if isinstance(rust_req.path_params, str) else {}
        )

        self.method: str = rust_req.method
        self.path: str = rust_req.path
        self._body_bytes: bytes = rust_req.body
        self._json_cache: Optional[dict[str, Any]] = None
        self._text_cache: Optional[str] = None

    def text(self) -> str:
        """Get the body as a UTF-8 string."""
        if self._text_cache is None:
            self._text_cache = bytearray(self._body_bytes).decode("utf-8")
        return self._text_cache

    def json(self) -> dict[str, Any]:
        """Parse the body as JSON."""
        if self._json_cache is None:
            self._json_cache = json.loads(self.text())
        return self._json_cache

    @property
    def body(self) -> bytes:
        "Get the raw request body bytes."
        return bytes(self._body_bytes)

    @property
    def cookies(self) -> dict[str, str]:
        "Get the request cookies as a dictionary."
        cookie_header = self.headers.get("cookie", "")
        if not cookie_header:
            return {}
        cookies: dict[str, str] = {}
        for part in cookie_header.split(";"):
            part = part.strip()
            if "=" in part:
                key, _, value = part.partition("=")
                cookies[key.strip()] = value.strip()
        return cookies
