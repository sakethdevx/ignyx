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
    Uses lazy property access — headers, query params, and path params stay
    in Rust memory and only cross the FFI boundary when explicitly accessed.
    """

    __slots__ = (
        "_rust_req",
        "method",
        "path",
        "_body_bytes",
        "_headers_cache",
        "_query_params_cache",
        "_path_params_cache",
        "_json_cache",
        "_text_cache",
    )

    def __init__(self, rust_req: _RustRequest) -> None:
        "Initialize the request wrapper."
        self._rust_req: _RustRequest = rust_req
        self.method: str = rust_req.method
        self.path: str = rust_req.path
        self._body_bytes: bytes = rust_req.body
        self._headers_cache: Optional[Headers] = None
        self._query_params_cache: Optional[dict[str, Any]] = None
        self._path_params_cache: Optional[dict[str, Any]] = None
        self._json_cache: Optional[dict[str, Any]] = None
        self._text_cache: Optional[str] = None

    @property
    def headers(self) -> Headers:
        """Lazy: headers stay in Rust memory until first access."""
        if self._headers_cache is None:
            self._headers_cache = Headers(self._rust_req.get_all_headers())
        return self._headers_cache

    @headers.setter
    def headers(self, value: Any) -> None:
        "Set headers (accepts dict or Headers)."
        self._headers_cache = value if isinstance(value, Headers) else Headers(value)

    @property
    def query_params(self) -> dict[str, Any]:
        """Lazy: query params stay in Rust memory until first access."""
        if self._query_params_cache is None:
            self._query_params_cache = dict(self._rust_req.get_all_query_params())
        return self._query_params_cache

    @query_params.setter
    def query_params(self, value: dict[str, Any]) -> None:
        "Set query params."
        self._query_params_cache = value

    @property
    def path_params(self) -> dict[str, Any]:
        """Lazy: path params stay in Rust memory until first access."""
        if self._path_params_cache is None:
            self._path_params_cache = dict(self._rust_req.get_all_path_params())
        return self._path_params_cache

    @path_params.setter
    def path_params(self, value: dict[str, Any]) -> None:
        "Set path params."
        self._path_params_cache = value

    def text(self) -> str:
        """Get the body as a UTF-8 string."""
        if self._text_cache is None:
            self._text_cache = bytearray(self._body_bytes).decode("utf-8")
        return self._text_cache

    def json(self) -> dict[str, Any]:
        """Parse the body as JSON."""
        if self._json_cache is None:
            import json

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
