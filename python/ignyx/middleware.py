"""
Middleware system for Ignyx.
Supports before, after, and error middleware.
"""

import time
import traceback
from collections import defaultdict
from typing import Any, Optional


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
        allow_origins: list[str] = None,
        allow_methods: list[str] = None,
        allow_headers: list[str] = None,
        allow_credentials: bool = False,
        max_age: int = 86400,
    ):
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]
        self.allow_credentials = allow_credentials
        self.max_age = max_age

    def after_request(self, request, response):
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

    def __init__(self, debug: bool = False):
        self.debug = debug

    def on_error(self, request, error):
        from ignyx.exceptions import HTTPException
        if isinstance(error, HTTPException):
            return None
        if self.debug:
            return {
                "error": type(error).__name__,
                "detail": str(error),
                "traceback": traceback.format_exception(type(error), error, error.__traceback__),
            }, 500
        else:
            return {
                "detail": "An unexpected error occurred",
            }, 500

class RateLimitMiddleware(Middleware):
    def __init__(self, requests: int = 100, window: int = 60):
        self.max_requests = requests
        self.window = window
        self._store: dict = defaultdict(list)

    def before_request(self, request):
        ip = request.headers.get("x-forwarded-for") or request.headers.get("x-real-ip") or "unknown"
        now = time.monotonic()
        self._store[ip] = [t for t in self._store[ip] if now - t < self.window]

        if len(self._store[ip]) >= self.max_requests:
            from ignyx.exceptions import HTTPException
            raise HTTPException(
                429,
                "Rate limit exceeded",
                headers={"Retry-After": str(self.window)}
            )

        self._store[ip].append(now)
        return request

class AccessLogMiddleware(Middleware):
    def __init__(self, logger_name: str = "ignyx.access"):
        import logging
        self.logger = logging.getLogger(logger_name)

    def before_request(self, request):
        request._ignyx_start = time.monotonic()
        return request

    def after_request(self, request, response):
        start = getattr(request, "_ignyx_start", time.monotonic())
        duration = (time.monotonic() - start) * 1000

        status = 200
        if hasattr(response, "status_code"):
            status = response.status_code
        elif isinstance(response, tuple) and len(response) > 1:
            status = response[1]

        self.logger.info(f"{request.method} {request.path} {status} {duration:.1f}ms")
        return response
