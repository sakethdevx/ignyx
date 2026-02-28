class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str = None, headers: dict = None):
        self.status_code = status_code
        self.detail = detail or ""
        self.headers = headers or {}

    def __repr__(self):
        return f"HTTPException(status_code={self.status_code}, detail={self.detail!r})"
