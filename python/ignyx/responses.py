import os

class BaseResponse:
    def __init__(self, content, status_code=200, headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}
        self.content_type = "text/plain"

    def render(self):
        return self.content

    def set_cookie(self, key: str, value: str, max_age: int = None,
                   httponly: bool = False, secure: bool = False,
                   samesite: str = "lax", path: str = "/"):
        cookie = f"{key}={value}; Path={path}; SameSite={samesite}"
        if max_age is not None:
            cookie += f"; Max-Age={max_age}"
        if httponly:
            cookie += "; HttpOnly"
        if secure:
            cookie += "; Secure"
        self.headers["set-cookie"] = cookie

    def delete_cookie(self, key: str, path: str = "/"):
        self.headers["set-cookie"] = f"{key}=; Path={path}; Max-Age=0"


class JSONResponse(BaseResponse):
    def __init__(self, content, status_code=200, headers=None):
        super().__init__(content, status_code, headers)
        self.content_type = "application/json"

    def render(self):
        import json
        return json.dumps(self.content)


class HTMLResponse(BaseResponse):
    def __init__(self, content, status_code=200, headers=None):
        super().__init__(content, status_code, headers)
        self.content_type = "text/html; charset=utf-8"


class PlainTextResponse(BaseResponse):
    def __init__(self, content, status_code=200, headers=None):
        super().__init__(content, status_code, headers)
        self.content_type = "text/plain; charset=utf-8"


class RedirectResponse(BaseResponse):
    def __init__(self, url, status_code=302, headers=None):
        super().__init__("", status_code, headers or {})
        self.content_type = "text/plain"
        self.headers["location"] = url


class FileResponse(BaseResponse):
    def __init__(self, path, filename=None, status_code=200, headers=None):
        super().__init__("", status_code, headers or {})
        self.path = path
        self.filename = filename or path.split("/")[-1]
        self.content_type = "application/octet-stream"
        self.headers["content-disposition"] = f'attachment; filename="{self.filename}"'

    def render(self):
        import os
        # Safety rail: Prevent OOM crashes by capping in-memory file serving to 10MB
        max_size = 10 * 1024 * 1024 
        if os.path.exists(self.path) and os.path.getsize(self.path) > max_size:
            raise RuntimeError(
                f"File '{self.filename}' exceeds the 10MB limit for FileResponse. "
                "Large file streaming support is planned for Ignyx v0.3.0."
            )
            
        with open(self.path, "rb") as f:
            return f.read()
