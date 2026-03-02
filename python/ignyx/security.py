import base64
from typing import Any

from ignyx.exceptions import HTTPException


class OAuth2PasswordBearer:
    def __init__(self, token_url: str) -> None:
        self.token_url = token_url

    def __call__(self, request: Any) -> str:
        auth: str = request.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(
                401,
                "Not authenticated",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return str(auth[7:])

class APIKeyHeader:
    def __init__(self, name: str, auto_error: bool = True) -> None:
        self.name = name
        self.auto_error = auto_error

    def __call__(self, request: Any) -> str:
        key: Any = request.headers.get(self.name.lower())
        if not key and self.auto_error:
            raise HTTPException(403, "API key required")
        return str(key)

class HTTPBasic:
    def __call__(self, request: Any) -> dict[str, str]:
        auth: str = request.headers.get("authorization", "")
        if not auth.startswith("Basic "):
            raise HTTPException(
                401,
                "Not authenticated",
                headers={"WWW-Authenticate": "Basic"}
            )
        try:
            decoded = base64.b64decode(auth[6:]).decode("utf-8")
        except Exception:
            raise HTTPException(401, "Invalid authentication credentials")

        username, _, password = decoded.partition(":")
        return {"username": username, "password": password}
