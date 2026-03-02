"""
Tests for the ASGI adapter (ignyx.asgi.IgnyxASGI).

Uses httpx.ASGITransport to drive the ASGI callable without starting a real
server, keeping tests fully in-process and fast.

Coverage:
  - Basic GET routing via ASGI
  - Path parameters (type coercion)
  - Query parameters
  - POST with JSON body / Pydantic model
  - BaseResponse subclasses (JSONResponse, HTMLResponse, RedirectResponse)
  - Streaming responses (StreamingResponse, EventSourceResponse)
  - Lifespan startup and shutdown handlers
  - Exception handling (HTTPException → correct status)
  - 404 for unregistered paths
  - Dependency injection via Depends()
  - BackgroundTasks injection
"""

import asyncio
import time

import httpx
import pytest

from ignyx import Depends, HTTPException, Ignyx
from ignyx.depends import BackgroundTask, BackgroundTasks
from ignyx.request import Request
from ignyx.responses import (
    EventSourceResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    StreamingResponse,
)


# ─── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def asgi_client():
    """Build a simple Ignyx app and return an httpx.AsyncClient over ASGI."""
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

    asgi_app = app.asgi()
    transport = httpx.ASGITransport(app=asgi_app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


# ─── basic routing ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_asgi_root(asgi_client):
    r = await asgi_client.get("/")
    assert r.status_code == 200
    assert r.json() == {"hello": "world"}


@pytest.mark.asyncio
async def test_asgi_path_param_int(asgi_client):
    r = await asgi_client.get("/users/42")
    assert r.status_code == 200
    assert r.json() == {"user_id": 42}


@pytest.mark.asyncio
async def test_asgi_query_params(asgi_client):
    r = await asgi_client.get("/search?q=ignyx&limit=10")
    assert r.status_code == 200
    assert r.json() == {"q": "ignyx", "limit": 10}


@pytest.mark.asyncio
async def test_asgi_query_default(asgi_client):
    r = await asgi_client.get("/search?q=test")
    assert r.status_code == 200
    assert r.json() == {"q": "test", "limit": 5}


@pytest.mark.asyncio
async def test_asgi_post_json_body(asgi_client):
    r = await asgi_client.post("/echo", json={"key": "value"})
    assert r.status_code == 200
    assert r.json() == {"key": "value"}


# ─── response types ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_asgi_html_response(asgi_client):
    r = await asgi_client.get("/html")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<h1>Hello</h1>" in r.text


@pytest.mark.asyncio
async def test_asgi_plain_text_response(asgi_client):
    r = await asgi_client.get("/plain")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]
    assert r.text == "hello text"


@pytest.mark.asyncio
async def test_asgi_redirect_response(asgi_client):
    r = await asgi_client.get("/redirect", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/health"


@pytest.mark.asyncio
async def test_asgi_str_html(asgi_client):
    r = await asgi_client.get("/str-html")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


@pytest.mark.asyncio
async def test_asgi_tuple_response(asgi_client):
    r = await asgi_client.get("/tuple")
    assert r.status_code == 201
    assert r.headers.get("x-custom") == "yes"
    assert r.json() == {"msg": "created"}


# ─── streaming ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_asgi_streaming(asgi_client):
    r = await asgi_client.get("/stream")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]
    assert r.text == "chunk0\nchunk1\nchunk2\n"


@pytest.mark.asyncio
async def test_asgi_sse(asgi_client):
    r = await asgi_client.get("/sse")
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    assert "data: 0" in r.text


# ─── errors ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_asgi_http_exception(asgi_client):
    r = await asgi_client.get("/raise")
    assert r.status_code == 403
    assert "forbidden" in r.json().get("detail", "")


@pytest.mark.asyncio
async def test_asgi_404(asgi_client):
    r = await asgi_client.get("/not-registered")
    assert r.status_code == 404
    assert r.json()["error"] == "not found"


# ─── dependency injection ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_asgi_depends_injection(asgi_client):
    r = await asgi_client.get("/di", headers={"x-token": "my-token"})
    assert r.status_code == 200
    assert r.json() == {"token": "my-token"}


# ─── BackgroundTasks ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_asgi_background_tasks_injected(asgi_client):
    """Route handler receives a BackgroundTasks instance and response is immediate."""
    r = await asgi_client.post("/bg")
    assert r.status_code == 200
    assert r.json() == {"queued": True}


# ─── lifespan ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_asgi_lifespan():
    """Startup and shutdown handlers are invoked during ASGI lifespan."""
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

    # Manually drive the lifespan ASGI cycle
    startup_q: asyncio.Queue = asyncio.Queue()
    send_q: asyncio.Queue = asyncio.Queue()

    async def receive():
        return await startup_q.get()

    async def send(msg):
        await send_q.put(msg)

    scope = {"type": "lifespan", "asgi": {"version": "3.0"}}

    await startup_q.put({"type": "lifespan.startup"})
    await startup_q.put({"type": "lifespan.shutdown"})

    await asgi_app(scope, receive, send)

    events = [send_q.get_nowait() for _ in range(send_q.qsize())]
    event_types = [e["type"] for e in events]

    assert "lifespan.startup.complete" in event_types
    assert "lifespan.shutdown.complete" in event_types
    assert log == ["started", "stopped"]


@pytest.mark.asyncio
async def test_asgi_lifespan_sync_handlers():
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
    startup_q: asyncio.Queue = asyncio.Queue()
    send_q: asyncio.Queue = asyncio.Queue()

    await startup_q.put({"type": "lifespan.startup"})
    await startup_q.put({"type": "lifespan.shutdown"})

    async def receive():
        return await startup_q.get()

    async def send(msg):
        await send_q.put(msg)

    scope = {"type": "lifespan"}
    await asgi_app(scope, receive, send)

    assert log == ["sync_started", "sync_stopped"]
