"""
Ignyx — Ignite your API. Built in Rust, runs in Python.
A high-performance Python web framework powered by Rust.
"""

from ignyx.app import Ignyx
from ignyx._core import Request, Response
from ignyx.middleware import Middleware
from ignyx.depends import Depends, BackgroundTask
from ignyx.router import Router
from ignyx.responses import (
    JSONResponse, HTMLResponse, PlainTextResponse,
    RedirectResponse, FileResponse
)
from ignyx.uploads import UploadFile
from ignyx.exceptions import HTTPException
from ignyx.security import OAuth2PasswordBearer, APIKeyHeader, HTTPBasic
from ignyx.testclient import TestClient
from ignyx.staticfiles import StaticFiles
from ignyx.middleware import RateLimitMiddleware, AccessLogMiddleware

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
]
__version__ = "1.1.1"
