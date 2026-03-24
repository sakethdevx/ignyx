"""
ASGI adapter for Ignyx.

Allows Ignyx applications to run under any ASGI-compliant server —
Uvicorn, Hypercorn, Daphne, Gunicorn + UvicornWorker — without any code
changes to the application itself.

    # main.py
    from ignyx import Ignyx

    app = Ignyx()

    @app.get("/")
    def root():
        return {"hello": "world"}

    asgi_app = app.asgi()   # ← standard ASGI callable

    # uvicorn main:asgi_app --workers 4

All Ignyx features work identically in ASGI mode:
  ✓ Routing (including path parameters)
  ✓ Dependency injection (Depends)
  ✓ Background tasks (BackgroundTasks / BackgroundTask)
  ✓ Middleware (before_request / after_request / on_error)
  ✓ Lifespan (@app.on_startup / @app.on_shutdown)
  ✓ OpenAPI / Swagger / ReDoc docs
  ✓ Streaming responses (StreamingResponse / EventSourceResponse)
  ✓ Exception handlers
"""

from __future__ import annotations

import asyncio
import inspect
import json
import re
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote_plus

from ignyx.depends import BackgroundTask, BackgroundTasks, resolve_dependencies, unwrap_annotated
from ignyx.exceptions import HTTPException
from ignyx.request import Headers
from ignyx.responses import BaseResponse

# ─────────────────────────────────────────────────────────────────────────────
# Path-pattern helpers
# ─────────────────────────────────────────────────────────────────────────────

def _compile_path(pattern: str) -> re.Pattern[str]:
    """Convert an Ignyx path pattern to a compiled regex.

    ``{param}``  → ``(?P<param>[^/]+)``
    ``{*param}`` → ``(?P<param>.+)``   (wildcard / catch-all)
    """
    # Wildcard first to avoid double-substitution
    rx = re.sub(r"\{(\*[^}]+)\}", lambda m: r"(?P<%s>.+)" % m.group(1)[1:], pattern)
    rx = re.sub(r"\{([^}]+)\}", r"(?P<\1>[^/]+)", rx)
    return re.compile("^" + rx + r"$")


# ─────────────────────────────────────────────────────────────────────────────
# Lightweight request object for ASGI mode
# ─────────────────────────────────────────────────────────────────────────────

class ASGIRequest:
    """
    A thin clone of :class:`ignyx.request.Request` built entirely from the
    ASGI ``scope`` and ``receive`` callables.  Provides the same attribute
    interface so handlers and dependencies that accept ``request: Request``
    work unchanged in ASGI mode.
    """

    __slots__ = (
        "method",
        "path",
        "_scope",
        "_receive",
        "_body_bytes",
        "_headers_cache",
        "_query_params_cache",
        "path_params",
        "_json_cache",
        "_text_cache",
        "_cookies_cache",
    )

    def __init__(
        self,
        scope: Dict[str, Any],
        receive: Callable[..., Any],
        path_params: Optional[Dict[str, str]] = None,
    ) -> None:
        self.method: str = scope.get("method", "GET").upper()
        self.path: str = scope.get("path", "/")
        self._scope = scope
        self._receive = receive
        self._body_bytes: Optional[bytes] = None
        self._headers_cache: Optional[Headers] = None
        self._query_params_cache: Optional[Dict[str, Any]] = None
        self.path_params: Dict[str, str] = path_params or {}
        self._json_cache: Optional[Any] = None
        self._text_cache: Optional[str] = None
        self._cookies_cache: Optional[Dict[str, str]] = None

    # ── Headers ──────────────────────────────────────────────────────────────

    @property
    def headers(self) -> Headers:
        if self._headers_cache is None:
            raw: List[Tuple[bytes, bytes]] = self._scope.get("headers", [])
            self._headers_cache = Headers(
                {k.decode("latin-1"): v.decode("latin-1") for k, v in raw}
            )
        return self._headers_cache

    # ── Query params ─────────────────────────────────────────────────────────

    @property
    def query_params(self) -> Dict[str, Any]:
        if self._query_params_cache is None:
            qs: bytes = self._scope.get("query_string", b"")
            parsed = parse_qs(qs.decode("latin-1"), keep_blank_values=True)
            self._query_params_cache = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
        return self._query_params_cache

    # ── Cookies ──────────────────────────────────────────────────────────────

    @property
    def cookies(self) -> Dict[str, str]:
        if self._cookies_cache is None:
            cookie_str = self.headers.get("cookie", "")
            result: Dict[str, str] = {}
            for part in cookie_str.split(";"):
                part = part.strip()
                if "=" in part:
                    k, _, v = part.partition("=")
                    result[k.strip()] = unquote_plus(v.strip())
            self._cookies_cache = result
        return self._cookies_cache

    # ── Body ─────────────────────────────────────────────────────────────────

    async def body(self) -> bytes:
        if self._body_bytes is None:
            chunks: List[bytes] = []
            while True:
                message = await self._receive()
                chunks.append(message.get("body", b""))
                if not message.get("more_body", False):
                    break
            self._body_bytes = b"".join(chunks)
        return self._body_bytes

    async def json(self) -> Any:
        if self._json_cache is None:
            raw = await self.body()
            self._json_cache = json.loads(raw)
        return self._json_cache

    async def text(self) -> str:
        if self._text_cache is None:
            raw = await self.body()
            self._text_cache = raw.decode("utf-8", errors="replace")
        return self._text_cache


# ─────────────────────────────────────────────────────────────────────────────
# Pre-built routing table entry
# ─────────────────────────────────────────────────────────────────────────────

class _CompiledRoute:
    """A single compiled route entry used by the ASGI router."""

    __slots__ = ("method", "pattern", "handler", "dispatch", "path_template")

    def __init__(
        self,
        method: str,
        path: str,
        handler: Callable[..., Any],
        dispatch: Callable[..., Any],
    ) -> None:
        self.method: str = method.upper()
        self.path_template = path
        self.pattern: re.Pattern[str] = _compile_path(path)
        self.handler = handler
        self.dispatch = dispatch


# ─────────────────────────────────────────────────────────────────────────────
# Response serialisation helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _send_response(
    send: Callable[..., Any],
    status: int,
    content_type: str,
    body: bytes,
    extra_headers: Optional[Dict[str, str]] = None,
) -> None:
    headers: List[Tuple[bytes, bytes]] = [
        (b"content-type", content_type.encode()),
        (b"content-length", str(len(body)).encode()),
    ]
    for k, v in (extra_headers or {}).items():
        headers.append((k.lower().encode(), v.encode()))

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body, "more_body": False})


async def _send_streaming_response(
    send: Callable[..., Any],
    status: int,
    content_type: str,
    body_iterator: Any,
    is_async: bool,
    extra_headers: Optional[Dict[str, str]] = None,
) -> None:
    headers: List[Tuple[bytes, bytes]] = [
        (b"content-type", content_type.encode()),
        (b"transfer-encoding", b"chunked"),
    ]
    for k, v in (extra_headers or {}).items():
        headers.append((k.lower().encode(), v.encode()))

    await send({"type": "http.response.start", "status": status, "headers": headers})

    if is_async:
        async for chunk in body_iterator:
            data = chunk.encode() if isinstance(chunk, str) else chunk
            await send({"type": "http.response.body", "body": data, "more_body": True})
    else:
        for chunk in body_iterator:
            data = chunk.encode() if isinstance(chunk, str) else chunk
            await send({"type": "http.response.body", "body": data, "more_body": True})

    await send({"type": "http.response.body", "body": b"", "more_body": False})


def _serialize_result(result: Any) -> Tuple[int, str, bytes, Dict[str, str], bool, Any]:
    """Convert a handler return value to ``(status, content_type, body, headers, is_streaming, iterator)``.

    Mirrors the Rust ``call_python_handler`` response serialisation logic.
    ``is_streaming`` is True when the result has ``__ignyx_streaming__``.
    ``iterator`` is the body iterator when streaming, else None.
    """
    extra_headers: Dict[str, str] = {}
    status = 200

    # ── Tuple unpacking ──────────────────────────────────────────────────────
    if isinstance(result, tuple):
        parts = result
        result = parts[0] if parts else ""
        if len(parts) >= 2:
            status = int(parts[1])
        if len(parts) >= 3 and isinstance(parts[2], dict):
            extra_headers.update({k.lower(): v for k, v in parts[2].items()})
        # 4th element can be a BackgroundTask (already executed by dispatch)

    # ── Streaming ────────────────────────────────────────────────────────────
    if hasattr(result, "__ignyx_streaming__"):
        content_type: str = getattr(result, "content_type", "application/octet-stream")
        status = getattr(result, "status_code", status)
        if hasattr(result, "headers"):
            extra_headers.update(
                {k.lower(): v for k, v in (getattr(result, "headers", {}) or {}).items()}
            )
        return (
            status,
            content_type,
            b"",
            extra_headers,
            True,
            getattr(result, "body_iterator", None),
        )

    # ── BaseResponse subclass ────────────────────────────────────────────────
    if (
        isinstance(result, BaseResponse)
        and not isinstance(result, dict)
        and not isinstance(result, str)
    ):
        rendered = result.render()
        body_bytes: bytes
        if isinstance(rendered, bytes):
            body_bytes = rendered
        else:
            body_bytes = str(rendered).encode()
        extra_headers.update({k.lower(): v for k, v in (result.headers or {}).items()})
        return (result.status_code, result.content_type, body_bytes, extra_headers, False, None)

    # ── dict / list → JSON ────────────────────────────────────────────────────
    if isinstance(result, (dict, list, int, float, bool)):
        return (
            status,
            "application/json",
            json.dumps(result).encode(),
            extra_headers,
            False,
            None,
        )

    # ── str → HTML or JSON string ─────────────────────────────────────────────
    if isinstance(result, str):
        if result.lstrip().startswith("<"):
            return (status, "text/html; charset=utf-8", result.encode(), extra_headers, False, None)
        return (
            status,
            "application/json",
            json.dumps(result).encode(),
            extra_headers,
            False,
            None,
        )

    # ── Fallback: attempt JSON serialisation ─────────────────────────────────
    try:
        body_bytes = json.dumps(result).encode()
    except (TypeError, ValueError):
        body_bytes = str(result).encode()
    return (status, "application/json", body_bytes, extra_headers, False, None)


# ─────────────────────────────────────────────────────────────────────────────
# Parameter binding helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _build_kwargs(
    handler: Callable[..., Any],
    request: ASGIRequest,
    path_params: Dict[str, str],
    qi_overrides: Optional[Dict[Callable[..., Any], Any]] = None,
) -> Dict[str, Any]:
    """Build the keyword arguments dict to pass to the dispatch wrapper.

    Performs Python-side equivalents of what ``call_python_handler`` does in
    Rust: inject request, coerce path params, bind query params, parse body,
    resolve :class:`~ignyx.depends.Depends` dependencies.
    """
    try:
        sig = inspect.signature(handler)
    except (ValueError, TypeError):
        return {}

    kwargs: Dict[str, Any] = {}
    di_resolved = resolve_dependencies(handler, request, qi_overrides or {})
    kwargs.update(di_resolved)

    # Lazily read body once if we need it
    body_bytes: Optional[bytes] = None
    body_json: Any = None

    for name, param in sig.parameters.items():
        if name in kwargs:
            continue  # already resolved by DI

        ann = param.annotation
        if ann is inspect.Parameter.empty:
            ann = None
        else:
            ann = unwrap_annotated(ann)

        # ── request ──────────────────────────────────────────────────────────
        if name == "request":
            kwargs["request"] = request
            continue

        # ── BackgroundTasks / BackgroundTask → injected by dispatch ──────────
        if ann in (BackgroundTasks, BackgroundTask):
            continue  # dispatch wrapper will inject these

        # ── path params ───────────────────────────────────────────────────────
        if name in path_params:
            raw_val = path_params[name]
            if ann is not None and ann is not str:
                try:
                    kwargs[name] = ann(raw_val)
                except (ValueError, TypeError):
                    kwargs[name] = raw_val
            else:
                kwargs[name] = raw_val
            continue

        # ── query params ──────────────────────────────────────────────────────
        qp = request.query_params
        if name in qp:
            raw_val = qp[name]
            if ann is not None and ann is not str:
                try:
                    kwargs[name] = ann(raw_val)
                except (ValueError, TypeError):
                    kwargs[name] = raw_val
            else:
                kwargs[name] = raw_val
            continue

        # ── body param ───────────────────────────────────────────────────────
        if name == "body":
            if body_bytes is None:
                body_bytes = await request.body()
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type and body_bytes:
                if body_json is None:
                    try:
                        body_json = json.loads(body_bytes)
                    except json.JSONDecodeError:
                        body_json = {}
                # Try Pydantic validation if annotation looks like a model
                if ann is not None and hasattr(ann, "model_validate"):
                    try:
                        kwargs["body"] = ann.model_validate(body_json)
                    except Exception:
                        kwargs["body"] = body_json
                else:
                    kwargs["body"] = body_json
            elif body_bytes:
                kwargs["body"] = body_bytes.decode("utf-8", errors="replace")
            continue

        # ── default value ──────────────────────────────────────────────────
        if param.default is not inspect.Parameter.empty:
            # Don't pass it — let the function use its default
            continue

    return kwargs


# ─────────────────────────────────────────────────────────────────────────────
# Main ASGI application class
# ─────────────────────────────────────────────────────────────────────────────

class IgnyxASGI:
    """
    Standard ASGI 3.0 callable that wraps an :class:`~ignyx.app.Ignyx` app.

    Obtain an instance via ``app.asgi()`` — do not instantiate directly.
    """

    def __init__(self, app: Any) -> None:
        self._app = app
        self._compiled_routes: List[_CompiledRoute] = []
        self._rebuild_routes()

    # ── Route compilation ─────────────────────────────────────────────────────

    def _rebuild_routes(self) -> None:
        """Compile all registered routes to regex patterns."""
        self._compiled_routes = []
        for route in self._app._routes:
            self._compiled_routes.append(
                _CompiledRoute(
                    method=route["method"],
                    path=route["path"],
                    handler=route["handler"],
                    dispatch=route.get("dispatch", route["handler"]),
                )
            )

    def _match_route(
        self, method: str, path: str
    ) -> Optional[Tuple[_CompiledRoute, Dict[str, str]]]:
        """Return ``(compiled_route, path_params)`` for the first match, else ``None``."""
        for route in self._compiled_routes:
            if route.method != method.upper():
                continue
            m = route.pattern.match(path)
            if m:
                return route, m.groupdict()
        return None

    # ── ASGI entry point ──────────────────────────────────────────────────────

    async def __call__(
        self,
        scope: Dict[str, Any],
        receive: Callable[..., Any],
        send: Callable[..., Any],
    ) -> None:
        scope_type: str = scope.get("type", "http")

        if scope_type == "lifespan":
            await self._handle_lifespan(scope, receive, send)
        elif scope_type == "http":
            await self._handle_http(scope, receive, send)
        else:
            # websocket and other scopes are not handled in ASGI mode
            pass

    # ── Lifespan ─────────────────────────────────────────────────────────────

    async def _handle_lifespan(
        self,
        scope: Dict[str, Any],
        receive: Callable[..., Any],
        send: Callable[..., Any],
    ) -> None:
        while True:
            message = await receive()
            event_type: str = message.get("type", "")

            if event_type == "lifespan.startup":
                try:
                    for handler in self._app._startup_handlers:
                        if inspect.iscoroutinefunction(handler):
                            await handler()
                        else:
                            handler()
                    await send({"type": "lifespan.startup.complete"})
                except Exception as exc:  # noqa: BLE001
                    await send({"type": "lifespan.startup.failed", "message": str(exc)})
                    return

            elif event_type == "lifespan.shutdown":
                try:
                    for handler in self._app._shutdown_handlers:
                        if inspect.iscoroutinefunction(handler):
                            await handler()
                        else:
                            handler()
                    await send({"type": "lifespan.shutdown.complete"})
                except Exception as exc:  # noqa: BLE001
                    await send({"type": "lifespan.shutdown.failed", "message": str(exc)})
                return

    # ── HTTP handling ─────────────────────────────────────────────────────────

    async def _handle_http(
        self,
        scope: Dict[str, Any],
        receive: Callable[..., Any],
        send: Callable[..., Any],
    ) -> None:
        method: str = scope.get("method", "GET").upper()
        path: str = scope.get("path", "/")

        # Rebuild routes in case new routes were registered after __init__
        # (e.g. docs routes added by _register_docs_routes)
        if len(self._compiled_routes) != len(self._app._routes):
            self._rebuild_routes()

        request = ASGIRequest(scope, receive)

        # ── Route matching ────────────────────────────────────────────────────
        match = self._match_route(method, path)
        if match is None:
            # Try exception handler for 404
            err_resp = self._app._handle_exception(request, None, 404)
            if err_resp is not None:
                status, ct, body, hdrs, streaming, iterator = _serialize_result(err_resp)
                if streaming:
                    is_async = hasattr(getattr(err_resp, "body_iterator", None), "__aiter__")
                    await _send_streaming_response(send, status, ct, iterator, is_async, hdrs)
                else:
                    await _send_response(send, status, ct, body, hdrs)
            else:
                body_bytes = json.dumps({"error": "Not Found", "detail": "No route found"}).encode()
                await _send_response(send, 404, "application/json", body_bytes)
            return

        compiled_route, path_params = match
        request.path_params = path_params

        # ── Apply before_request middleware ───────────────────────────────────
        for mw in self._app._middlewares:
            if hasattr(mw, "before_request"):
                try:
                    result = mw.before_request(request)
                    if asyncio.iscoroutine(result):
                        request = await result
                    elif result is not None:
                        request = result
                except Exception:
                    pass

        # ── Build kwargs and call the dispatch wrapper ─────────────────────────
        try:
            kwargs = await _build_kwargs(
                compiled_route.handler,
                request,
                path_params,
                self._app._dependency_overrides,
            )
            dispatch = compiled_route.dispatch
            if inspect.iscoroutinefunction(dispatch):
                raw_result = await dispatch(**kwargs)
            else:
                raw_result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: dispatch(**kwargs)
                )

        except HTTPException as exc:
            err_resp = self._app._handle_exception(request, exc, exc.status_code)
            if err_resp is None:
                err_body = json.dumps({"detail": exc.detail}).encode()
                await _send_response(send, exc.status_code, "application/json", err_body)
            else:
                status, ct, body, hdrs, streaming, iterator = _serialize_result(err_resp)
                if streaming:
                    is_async = hasattr(iterator, "__aiter__")
                    await _send_streaming_response(send, status, ct, iterator, is_async, hdrs)
                else:
                    await _send_response(send, status, ct, body, hdrs)
            return

        except Exception as exc:
            # Try registered error middleware / exception handlers
            for mw in self._app._middlewares:
                if hasattr(mw, "on_error"):
                    mw_result = mw.on_error(request, exc)
                    if mw_result is not None:
                        raw_result = mw_result
                        break
            else:
                status_code = getattr(exc, "status_code", 500)
                err_resp = self._app._handle_exception(request, exc, status_code)
                if err_resp is not None:
                    raw_result = err_resp
                else:
                    err_body = json.dumps({"error": "Internal Server Error"}).encode()
                    await _send_response(send, 500, "application/json", err_body)
                    return

        # ── Apply after_request middleware ────────────────────────────────────
        for mw in self._app._middlewares:
            if hasattr(mw, "after_request"):
                try:
                    result = mw.after_request(request, raw_result)
                    if asyncio.iscoroutine(result):
                        raw_result = await result
                    elif result is not None:
                        raw_result = result
                except Exception:
                    pass

        # ── Serialize and send ────────────────────────────────────────────────
        status, content_type, body_bytes, extra_headers, is_streaming, iterator = (
            _serialize_result(raw_result)
        )

        if is_streaming:
            is_async_iter = hasattr(iterator, "__aiter__")
            await _send_streaming_response(
                send, status, content_type, iterator, is_async_iter, extra_headers
            )
        else:
            await _send_response(send, status, content_type, body_bytes, extra_headers)
