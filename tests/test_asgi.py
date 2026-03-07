"""
Tests for the ASGI adapter (ignyx.asgi.IgnyxASGI).

Uses ``httpx.ASGITransport`` to drive the ASGI callable in-process (no real
server started).  Every test is a *synchronous* function that calls
``asyncio.run()`` internally — no pytest-asyncio plugin required.

Coverage:
  - Basic GET routing
  - Path parameters (type coercion)
  - Query parameters (with defaults)
  - POST with JSON body
  - BaseResponse subclasses (JSONResponse, HTMLResponse, PlainTextResponse,
    RedirectResponse)
  - Streaming responses (StreamingResponse, EventSourceResponse)
  - Tuple response (body, status, headers)
  - Exception handling (HTTPException → correct status)
  - 404 for unregistered paths (custom exception handler)
  - Dependency injection via Depends()
  - BackgroundTasks injection
  - Lifespan: startup/shutdown (async + sync handlers)
"""

import asyncio

import httpx
import pytest
from ignyx import Depends, HTTPException, Ignyx
from ignyx.depends import BackgroundTasks
from ignyx.request import Request
from ignyx.responses import (
    EventSourceResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    StreamingResponse,
)

# ─── helpers ──────────────────────────────────────────────────────────────────

def _asgi_request(asgi_app, method: str, path: str, **kwargs):
    """Make a single HTTP request against an ASGI app synchronously."""
    async def _():
        transport = httpx.ASGITransport(app=asgi_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            return await c.request(method, path, **kwargs)
    return asyncio.run(_())


def _get(app, path, **kw):
    return _asgi_request(app, "GET", path, **kw)


def _post(app, path, **kw):
    return _asgi_request(app, "POST", path, **kw)


# ─── shared ASGI app fixture ──────────────────────────────────────────────────

@pytest.fixture(scope="module")
def asgi_app():
    """Build a small Ignyx app and expose its ASGI callable."""
    app = Ignyx(title="ASGI-Test", version="2.5.0")

    @app.get("/")
    def root():
        return {"hello": "world"}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/users/{user_id}")
    def get_user(user_id: int):
        return {"user_id": user_id}

    @app.get("/search")
    def search(q: str, limit: int = 5):
        return {"q": q, "limit": limit}

    @app.post("/echo")
    def echo(body: dict):
        return body

    @app.get("/html")
    def html_route():
        return HTMLResponse("<h1>Hello</h1>")

    @app.get("/redirect")
    def redirect_route():
        return RedirectResponse("/health", status_code=302)

    @app.get("/plain")
    def plain_route():
        return PlainTextResponse("hello text")

    @app.get("/raise")
    def raise_route():
        raise HTTPException(403, "forbidden")

    @app.get("/tuple")
    def tuple_route():
        return {"msg": "created"}, 201, {"x-custom": "yes"}

    @app.get("/str-html")
    def str_html():
        return "<p>HTML string</p>"

    @app.get("/stream")
    def stream_route():
        def gen():
            for i in range(3):
                yield f"chunk{i}\n"
        return StreamingResponse(gen(), media_type="text/plain")

    @app.get("/sse")
    def sse_route():
        def gen():
            for i in range(2):
                yield f"data: {i}\n\n"
        return EventSourceResponse(gen())

    def get_token(request: Request):
        return request.headers.get("x-token", "none")

    @app.get("/di")
    def di_route(token=Depends(get_token)):
        return {"token": token}

    @app.post("/bg")
    def bg_route(tasks: BackgroundTasks):
        tasks.add_task(lambda: None)
        return {"queued": True}

    @app.exception_handler(404)
    def not_found(request: Request, exc):
        return JSONResponse({"error": "not found"}, status_code=404)

    return app.asgi()


# ─── basic routing ─────────────────────────────────────────────────────────────

def test_asgi_root(asgi_app):
    r = _get(asgi_app, "/")
    assert r.status_code == 200
    assert r.json() == {"hello": "world"}


def test_asgi_health(asgi_app):
    r = _get(asgi_app, "/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_asgi_path_param_int(asgi_app):
    r = _get(asgi_app, "/users/42")
    assert r.status_code == 200
    assert r.json() == {"user_id": 42}


def test_asgi_query_params(asgi_app):
    r = _get(asgi_app, "/search?q=ignyx&limit=10")
    assert r.status_code == 200
    assert r.json() == {"q": "ignyx", "limit": 10}


def test_asgi_query_default(asgi_app):
    r = _get(asgi_app, "/search?q=test")
    assert r.status_code == 200
    assert r.json() == {"q": "test", "limit": 5}


def test_asgi_post_json_body(asgi_app):
    r = _post(asgi_app, "/echo", json={"key": "value"})
    assert r.status_code == 200
    assert r.json() == {"key": "value"}


# ─── response types ─────────────────────────────────────────────────────────────

def test_asgi_html_response(asgi_app):
    r = _get(asgi_app, "/html")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<h1>Hello</h1>" in r.text


def test_asgi_plain_text_response(asgi_app):
    r = _get(asgi_app, "/plain")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]
    assert r.text == "hello text"


def test_asgi_redirect_response(asgi_app):
    r = _asgi_request(asgi_app, "GET", "/redirect", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/health"


def test_asgi_str_html(asgi_app):
    r = _get(asgi_app, "/str-html")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_asgi_tuple_response(asgi_app):
    r = _get(asgi_app, "/tuple")
    assert r.status_code == 201
    assert r.headers.get("x-custom") == "yes"
    assert r.json() == {"msg": "created"}


# ─── streaming ─────────────────────────────────────────────────────────────────

def test_asgi_streaming(asgi_app):
    r = _get(asgi_app, "/stream")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]
    assert r.text == "chunk0\nchunk1\nchunk2\n"


def test_asgi_sse(asgi_app):
    r = _get(asgi_app, "/sse")
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    assert "data: 0" in r.text


# ─── errors ──────────────────────────────────────────────────────────────────

def test_asgi_http_exception(asgi_app):
    r = _get(asgi_app, "/raise")
    assert r.status_code == 403
    assert "forbidden" in r.json().get("detail", "")


def test_asgi_404(asgi_app):
    r = _get(asgi_app, "/not-registered")
    assert r.status_code == 404
    assert r.json()["error"] == "not found"


# ─── dependency injection ─────────────────────────────────────────────────────

def test_asgi_depends_injection(asgi_app):
    r = _asgi_request(asgi_app, "GET", "/di", headers={"x-token": "my-token"})
    assert r.status_code == 200
    assert r.json() == {"token": "my-token"}


# ─── BackgroundTasks ──────────────────────────────────────────────────────────

def test_asgi_background_tasks_injected(asgi_app):
    r = _post(asgi_app, "/bg")
    assert r.status_code == 200
    assert r.json() == {"queued": True}


# ─── lifespan ─────────────────────────────────────────────────────────────────

def test_asgi_lifespan_async():
    """Async startup and shutdown handlers are invoked."""
    app = Ignyx()
    log: list = []

    @app.on_startup
    async def startup():
        log.append("started")

    @app.on_shutdown
    async def shutdown():
        log.append("stopped")

    @app.get("/ping")
    def ping():
        return {"pong": True}

    asgi_app = app.asgi()

    async def _run():
        q: asyncio.Queue = asyncio.Queue()
        sent: list = []
        await q.put({"type": "lifespan.startup"})
        await q.put({"type": "lifespan.shutdown"})

        async def receive():
            return await q.get()

        async def send(msg):
            sent.append(msg)

        await asgi_app({"type": "lifespan", "asgi": {"version": "3.0"}}, receive, send)
        return sent

    sent = asyncio.run(_run())
    types = [e["type"] for e in sent]
    assert "lifespan.startup.complete" in types
    assert "lifespan.shutdown.complete" in types
    assert log == ["started", "stopped"]


def test_asgi_lifespan_sync():
    """Synchronous startup/shutdown handlers are called correctly."""
    app = Ignyx()
    log: list = []

    @app.on_startup
    def sync_start():
        log.append("sync_started")

    @app.on_shutdown
    def sync_stop():
        log.append("sync_stopped")

    asgi_app = app.asgi()

    async def _run():
        q: asyncio.Queue = asyncio.Queue()
        sent: list = []
        await q.put({"type": "lifespan.startup"})
        await q.put({"type": "lifespan.shutdown"})

        async def receive():
            return await q.get()

        async def send(msg):
            sent.append(msg)

        await asgi_app({"type": "lifespan"}, receive, send)
        return sent

    sent = asyncio.run(_run())
    types = [e["type"] for e in sent]
    assert "lifespan.startup.complete" in types
    assert "lifespan.shutdown.complete" in types
    assert log == ["sync_started", "sync_stopped"]



