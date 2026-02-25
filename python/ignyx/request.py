import json
from collections import UserDict
from ignyx._core import Request as _RustRequest

class Headers(UserDict):
    """Case-insensitive dictionary for HTTP headers."""
    def __setitem__(self, key, item):
        self.data[key.lower()] = item

    def __getitem__(self, key):
        return self.data[key.lower()]

    def __contains__(self, key):
        return key.lower() in self.data

    def __delitem__(self, key):
        del self.data[key.lower()]

    def get(self, key, default=None):
        return self.data.get(key.lower(), default)

class Request:
    """
    Python wrapper around the Rust Request object.
    Provides typed, native Python dictionary access to request properties.
    """
    def __init__(self, rust_req: _RustRequest):
        self._rust_req = rust_req
        
        # Parse JSON blocks eagerly to native Python dictionaries
        raw_headers = json.loads(rust_req.headers) if isinstance(rust_req.headers, str) else {}
        self.headers = Headers(raw_headers)
        self.query_params = json.loads(rust_req.query_params) if isinstance(rust_req.query_params, str) else {}
        self.path_params = json.loads(rust_req.path_params) if isinstance(rust_req.path_params, str) else {}
        
        self.method = rust_req.method
        self.path = rust_req.path
        self._body_bytes = rust_req.body
        self._json_cache = None

    def text(self) -> str:
        """Get the body as a UTF-8 string."""
        if not hasattr(self, "_text_cache"):
            self._text_cache = bytearray(self._body_bytes).decode("utf-8")
        return self._text_cache

    def json(self) -> dict:
        """Parse the body as JSON."""
        if self._json_cache is None:
            self._json_cache = json.loads(self.text())
        return self._json_cache

    @property
    def body(self) -> bytes:
        return bytes(self._body_bytes)

    @property
    def cookies(self) -> dict:
        cookie_header = self.headers.get("cookie", "")
        if not cookie_header:
            return {}
        cookies = {}
        for part in cookie_header.split(";"):
            part = part.strip()
            if "=" in part:
                key, _, value = part.partition("=")
                cookies[key.strip()] = value.strip()
        return cookies
