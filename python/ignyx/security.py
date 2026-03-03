import base64
from typing import Any, Dict

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


class JWTBearer:
    """
    Dependency that extracts and validates a Bearer JWT from the
    ``Authorization`` header using Rust-native JWT decoding.

    Usage::

        from ignyx import Ignyx, Depends
        from ignyx.security import JWTBearer

        jwt = JWTBearer(secret="your-secret", algorithm="HS256")

        app = Ignyx()

        @app.get("/protected")
        def protected(payload=Depends(jwt)):
            return {"user": payload.get("sub")}

    Parameters
    ----------
    secret:
        HMAC secret (for HS256/HS384/HS512) or PEM key string for asymmetric
        algorithms.
    algorithm:
        JWT algorithm — default ``"HS256"``.
    validate_exp:
        Whether to enforce the ``exp`` claim — default ``True``.  Set to
        ``False`` during testing to use tokens without an expiry.
    """

    def __init__(
        self,
        secret: str,
        algorithm: str = "HS256",
        validate_exp: bool = True,
    ) -> None:
        from ignyx._core import JwtDecoder  # Rust-native codec
        self._decoder = JwtDecoder(
            secret=secret,
            algorithm=algorithm,
            validate_exp=validate_exp,
        )

    def __call__(self, request: Any) -> Dict[str, Any]:
        auth: str = request.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            raise HTTPException(
                401,
                "Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = auth[7:].strip()
        try:
            return self._decoder.decode(token)  # type: ignore[return-value]
        except Exception:
            raise HTTPException(
                401,
                "Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
