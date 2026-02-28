from typing import Any, Dict, Optional


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: Optional[str] = None, headers: Optional[Dict[Any, Any]] = None):
        self.status_code = status_code
        self.detail = detail
        self.headers = headers

    def __repr__(self):
        return f"HTTPException(status_code={self.status_code}, detail={self.detail!r})"
