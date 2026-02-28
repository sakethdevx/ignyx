import os
from typing import Any, Dict, Optional


class BaseResponse:
    """
    Base class for all Ignyx responses.
    """
    def __init__(self, content: Any, status_code: int = 200, headers: Optional[Dict[str, str]] = None) -> None:
        self.content: Any = content
        self.status_code: int = status_code
        self.headers: Dict[str, str] = headers or {}
        self.content_type: str = "text/plain"

    def render(self) -> Any:
        return self.content

    def set_cookie(
        self,
        key: str,
        value: str,
        max_age: Optional[int] = None,
        httponly: bool = False,
        secure: bool = False,
        samesite: str = "lax",
        path: str = "/"
    ) -> None:
        """Set a cookie on the response."""
        cookie = f"{key}={value}; Path={path}; SameSite={samesite}"
        if max_age is not None:
            cookie += f"; Max-Age={max_age}"
        if httponly:
            cookie += "; HttpOnly"
        if secure:
            cookie += "; Secure"
        self.headers["set-cookie"] = cookie

    def delete_cookie(self, key: str, path: str = "/") -> None:
        """Delete a cookie from the response."""
        self.headers["set-cookie"] = f"{key}=; Path={path}; Max-Age=0"


class JSONResponse(BaseResponse):
    """
    Returns a JSON encoded response.
    """
    def __init__(self, content: Any, status_code: int = 200, headers: Optional[Dict[str, str]] = None) -> None:
        super().__init__(content, status_code, headers)
        self.content_type = "application/json"

    def render(self) -> str:
        import json
        return json.dumps(self.content)


class HTMLResponse(BaseResponse):
    """
    Returns an HTML response.
    """
    def __init__(self, content: str, status_code: int = 200, headers: Optional[Dict[str, str]] = None) -> None:
        super().__init__(content, status_code, headers)
        self.content_type = "text/html; charset=utf-8"


class PlainTextResponse(BaseResponse):
    """
    Returns a plain text response.
    """
    def __init__(self, content: str, status_code: int = 200, headers: Optional[Dict[str, str]] = None) -> None:
        super().__init__(content, status_code, headers)
        self.content_type = "text/plain; charset=utf-8"


class RedirectResponse(BaseResponse):
    """
    Returns an HTTP redirect.
    """
    def __init__(self, url: str, status_code: int = 302, headers: Optional[Dict[str, str]] = None) -> None:
        super().__init__("", status_code, headers)
        self.content_type = "text/plain"
        self.headers["location"] = url


class FileResponse(BaseResponse):
    """
    Returns a file attachment response.
    """
    def __init__(
        self,
        path: str,
        filename: Optional[str] = None,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None
    ) -> None:
        super().__init__("", status_code, headers)
        self.path: str = path
        self.filename: str = filename or path.split("/")[-1]
        self.content_type: str = "application/octet-stream"
        self.headers["content-disposition"] = f'attachment; filename="{self.filename}"'

    def render(self) -> bytes:
        # Safety rail: Prevent OOM crashes by capping in-memory file serving to 10MB
        max_size = 10 * 1024 * 1024
        if os.path.exists(self.path) and os.path.getsize(self.path) > max_size:
            raise RuntimeError(
                f"File '{self.filename}' exceeds the 10MB limit for FileResponse. "
                "Large file streaming support is planned for Ignyx v0.3.0."
            )

        with open(self.path, "rb") as f:
            return f.read()
