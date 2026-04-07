"""
Ignyx — Ignite your API. Built in Rust, runs in Python.
A high-performance Python web framework powered by Rust.
"""

from ignyx._core import Request, Response
from ignyx.app import Ignyx
from ignyx.depends import BackgroundTask, BackgroundTasks, Depends
from ignyx.exceptions import HTTPException
from ignyx.middleware import (
    AccessLogMiddleware,
    CORSMiddleware,
    ErrorHandlerMiddleware,
    GZipMiddleware,
    Middleware,
)
from ignyx.pagination import Page, paginate
from ignyx.responses import (
    EventSourceResponse,
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    StreamingResponse,
)
from ignyx.router import Router
from ignyx.security import APIKeyHeader, HTTPBasic, JWTBearer, OAuth2PasswordBearer
from ignyx.staticfiles import StaticFiles
from ignyx.testclient import TestClient
from ignyx.uploads import UploadFile

__all__ = [
    "Ignyx",
    "Request",
    "Response",
    "Middleware",
    "Depends",
    "Page",
    "Router",
    "JSONResponse",
    "HTMLResponse",
    "PlainTextResponse",
    "RedirectResponse",
    "FileResponse",
    "StreamingResponse",
    "EventSourceResponse",
    "UploadFile",
    "BackgroundTask",
    "BackgroundTasks",
    "HTTPException",
    "OAuth2PasswordBearer",
    "APIKeyHeader",
    "HTTPBasic",
    "JWTBearer",
    "TestClient",
    "StaticFiles",
    "AccessLogMiddleware",
    "CORSMiddleware",
    "ErrorHandlerMiddleware",
    "GZipMiddleware",
    "paginate",
]
__version__ = "3.1.0"
