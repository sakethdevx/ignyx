"""
Ignyx — Ignite your API. Built in Rust, runs in Python.
A high-performance Python web framework powered by Rust.
"""

from ignyx._core import Request, Response
from ignyx.app import Ignyx
from ignyx.depends import BackgroundTask, Depends
from ignyx.exceptions import HTTPException
from ignyx.middleware import (
    AccessLogMiddleware,
    CORSMiddleware,
    ErrorHandlerMiddleware,
    Middleware,
    RateLimitMiddleware,
)
from ignyx.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
)
from ignyx.router import Router
from ignyx.security import APIKeyHeader, HTTPBasic, OAuth2PasswordBearer
from ignyx.staticfiles import StaticFiles
from ignyx.testclient import TestClient
from ignyx.uploads import UploadFile

__all__ = [
    "Ignyx",
    "Request",
    "Response",
    "Middleware",
    "Depends",
    "Router",
    "JSONResponse",
    "HTMLResponse",
    "PlainTextResponse",
    "RedirectResponse",
    "FileResponse",
    "UploadFile",
    "BackgroundTask",
    "HTTPException",
    "OAuth2PasswordBearer",
    "APIKeyHeader",
    "HTTPBasic",
    "TestClient",
    "StaticFiles",
    "RateLimitMiddleware",
    "AccessLogMiddleware",
    "CORSMiddleware",
    "ErrorHandlerMiddleware",
]
__version__ = "2.1.3"
