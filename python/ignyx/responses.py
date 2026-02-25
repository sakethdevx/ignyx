class BaseResponse:
    def __init__(self, content, status_code=200, headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}
        self.content_type = "text/plain"

    def render(self):
        return self.content


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
        with open(self.path, "rb") as f:
            return f.read()
