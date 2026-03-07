"""
Middleware system for Ignyx.
Supports before, after, and error middleware.
"""

import time
import traceback
from collections import defaultdict  # noqa: F401  # kept for backward compat
from typing import Any, Dict, List, Optional, Tuple, Union


class Middleware:
    """
    Base middleware class. Subclass this and override
    before_request, after_request, or on_error.

    Usage:
        class LoggingMiddleware(Middleware):
            async def before_request(self, request):
                print(f"Request: {request.method} {request.path}")
                return request

            async def after_request(self, request, response):
                print(f"Response: {response.status_code}")
                return response

        app.add_middleware(LoggingMiddleware())
    """

    def before_request(self, request: Any) -> Any:
        """Called before the route handler. Return the (possibly modified) request."""
        return request

    def after_request(self, request: Any, response: Any) -> Any:
        """Called after the route handler. Return the (possibly modified) response."""
        return response

    def on_error(self, request: Any, error: Exception) -> Optional[Any]:
        """Called when an error occurs. Return a response to override default error handling."""
        return None


class CORSMiddleware(Middleware):
    """
    CORS middleware for cross-origin requests.

    Usage:
        app.add_middleware(CORSMiddleware(
            allow_origins=["*"],
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Content-Type", "Authorization"],
        ))
    """

    def __init__(
        self,
        allow_origins: Optional[List[str]] = None,
        allow_methods: Optional[List[str]] = None,
        allow_headers: Optional[List[str]] = None,
        allow_credentials: bool = False,
        max_age: int = 86400,
    ) -> None:
        "Initialize CORSMiddleware with policy details."
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials
        self.max_age = max_age

    def after_request(self, request: Any, response: Any) -> Any:
        "Add CORS headers to the response."
        # We need to ensure we return a tuple of (body, status, headers)

        body = response
        status = 200
        headers = {}

        if isinstance(response, tuple):
            body = response[0]
            status = response[1] if len(response) > 1 else 200
            headers = response[2] if len(response) > 2 else {}
        elif not isinstance(response, (dict, str)):
            # If it's some other object, just return it
            return response

        # Add CORS headers
        # We use lowercase keys for consistency
        headers["access-control-allow-origin"] = ", ".join(self.allow_origins)
        headers["access-control-allow-methods"] = ", ".join(self.allow_methods)
        headers["access-control-allow-headers"] = ", ".join(self.allow_headers)
        if self.allow_credentials:
            headers["access-control-allow-credentials"] = "true"
        headers["access-control-max-age"] = str(self.max_age)

        return (body, status, headers)


class ErrorHandlerMiddleware(Middleware):
    """
    Error handling middleware with dev/prod modes.
    In dev mode: returns full stack traces.
    In prod mode: returns clean JSON errors.
    """

    def __init__(self, debug: bool = False) -> None:
        "Initialize ErrorHandlerMiddleware."
        self.debug = debug

    def on_error(self, request: Any, error: Exception) -> Optional[Union[Dict[str, Any], Tuple[Dict[str, Any], int]]]:
        "Catch and format exceptions into JSON responses."
        from ignyx.exceptions import HTTPException

        if isinstance(error, HTTPException):
            return None
        if self.debug:
            return {
                "error": type(error).__name__,
                "detail": str(error),
                "traceback": traceback.format_exception(
                    type(error), error, error.__traceback__
                ),
            }, 500
        else:
            return {
                "detail": "An unexpected error occurred",
            }, 500


class AccessLogMiddleware(Middleware):
    "Middleware for logging request details and duration."

    def __init__(self, logger_name: str = "ignyx.access") -> None:
        "Initialize access logger."
        import logging

        self.logger = logging.getLogger(logger_name)

    def before_request(self, request: Any) -> Any:
        "Record start time."
        request._ignyx_start = time.monotonic()
        return request

    def after_request(self, request: Any, response: Any) -> Any:
        "Log request duration and status."
        start = getattr(request, "_ignyx_start", time.monotonic())
        duration = (time.monotonic() - start) * 1000

        status = 200
        if hasattr(response, "status_code"):
            status = response.status_code
        elif isinstance(response, tuple) and len(response) > 1:
            status = response[1]

        self.logger.info(f"{request.method} {request.path} {status} {duration:.1f}ms")
        return response


class GZipMiddleware(Middleware):
    """
    GZip compression middleware.

    When added, responses larger than ``minimum_size`` bytes are compressed
    with GZip **in Rust** (zero Python overhead).  The Python object is only
    used as a configuration carrier — the Rust server extracts ``minimum_size``
    at startup and performs the actual compression natively.

    Usage:
        app.add_middleware(GZipMiddleware(minimum_size=500))
    """

    def __init__(self, minimum_size: int = 500) -> None:
        "Initialize GZip middleware."
        self.minimum_size = minimum_size


class SessionMiddleware(Middleware):
    """
    Stateful session management middleware powered by Rust AES-GCM encryption.

    This middleware enables the `request.session` dictionary.
    The secret key must be provided to securely encrypt and tamper-proof the session cookie.

    Usage:
        app.add_middleware(SessionMiddleware(secret_key="your-32-byte-secret-key-here"))
    """

    def __init__(self, secret_key: str) -> None:
        "Initialize Session middleware with a secret key."
        self.secret_key = secret_key

