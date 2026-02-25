"""
Ignyx — Ignite your API. Built in Rust, runs in Python.
A high-performance Python web framework powered by Rust.
"""

from ignyx.app import Ignyx
from ignyx._core import Request, Response
from ignyx.middleware import Middleware
from ignyx.depends import Depends
from ignyx.router import Router
from ignyx.responses import (
    JSONResponse, HTMLResponse, PlainTextResponse,
    RedirectResponse, FileResponse
)

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
]
__version__ = "0.1.0"
