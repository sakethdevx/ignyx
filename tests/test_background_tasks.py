"""
Tests for the BackgroundTasks engine (ignyx.depends).

Each test exercises a distinct aspect:
  - task injection via route parameter annotation
  - fire-and-forget (does not block HTTP response)
  - sync callable execution
  - async callable execution
  - multiple tasks per request
  - BackgroundTask (singular) backward-compat subclass
"""

import asyncio
import time

from ignyx import Ignyx
from ignyx.depends import BackgroundTask, BackgroundTasks
from ignyx.testclient import TestClient

# ─── helpers ─────────────────────────────────────────────────────────────────

def _new_client_with_bg_route() -> tuple:
    """Return (client, shared_results_list) for a simple BG-task POST route."""
    app = Ignyx()
    results: list = []

    def slow_work(msg: str) -> None:
        time.sleep(0.05)
        results.append(msg)

    @app.post("/notify")
    def notify(tasks: BackgroundTasks):
        tasks.add_task(slow_work, "hello")
        return {"queued": True}

    return TestClient(app), results


# ─── tests ────────────────────────────────────────────────────────────────────

def test_background_tasks_injected():
    """Route handler receives a fresh BackgroundTasks instance."""
    app = Ignyx()
    received: list = []

    @app.get("/check")
    def check(tasks: BackgroundTasks):
        received.append(type(tasks).__name__)
        return {"ok": True}

    client = TestClient(app)
    r = client.get("/check")
    assert r.status_code == 200
    assert received == ["BackgroundTasks"]


def test_background_tasks_response_immediate():
    """HTTP response is returned before the background task completes."""
    client, results = _new_client_with_bg_route()

    start = time.monotonic()
    r = client.post("/notify")
    elapsed = time.monotonic() - start

    assert r.status_code == 200
    # Response must arrive quickly (well under the 50 ms task sleep)
    assert elapsed < 0.5, f"Response took too long: {elapsed:.3f}s"


def test_background_tasks_sync_executes():
    """Sync task eventually runs after the response."""
    client, results = _new_client_with_bg_route()
    client.post("/notify")

    # Wait long enough for the 50 ms task to finish
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and "hello" not in results:
        time.sleep(0.05)

    assert results == ["hello"]


def test_background_tasks_multiple():
    """Multiple tasks are all executed."""
    app = Ignyx()
    log: list = []

    def record(tag: str) -> None:
        time.sleep(0.02)
        log.append(tag)

    @app.post("/multi")
    def multi(tasks: BackgroundTasks):
        tasks.add_task(record, "a")
        tasks.add_task(record, "b")
        tasks.add_task(record, "c")
        return {"count": 3}

    client = TestClient(app)
    r = client.post("/multi")
    assert r.status_code == 200

    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and len(log) < 3:
        time.sleep(0.05)

    assert sorted(log) == ["a", "b", "c"]


def test_background_tasks_async_callable():
    """Async callables are scheduled correctly."""
    app = Ignyx()
    log: list = []

    async def async_work(value: str) -> None:
        await asyncio.sleep(0.05)
        log.append(value)

    @app.post("/async")
    def submit(tasks: BackgroundTasks):
        tasks.add_task(async_work, "async-done")
        return {"ok": True}

    client = TestClient(app)
    client.post("/async")

    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and "async-done" not in log:
        time.sleep(0.05)

    assert "async-done" in log


def test_background_task_singular_backward_compat():
    """BackgroundTask (singular) still works as before."""
    app = Ignyx()
    results: list = []

    def do_work(msg: str) -> None:
        time.sleep(0.05)
        results.append(msg)

    @app.post("/legacy")
    def legacy(task: BackgroundTask):
        task.add_task(do_work, "legacy")
        return {"status": "accepted"}

    client = TestClient(app)
    r = client.post("/legacy")
    assert r.status_code == 200

    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and "legacy" not in results:
        time.sleep(0.05)

    assert results == ["legacy"]


def test_background_tasks_add_alias():
    """``add()`` is an alias for ``add_task()``."""
    bt = BackgroundTasks()
    log: list = []

    def fn() -> None:
        log.append(1)

    bt.add(fn)
    bt.execute()
    time.sleep(0.2)
    assert log == [1]


def test_background_tasks_len():
    """``len()`` returns the number of queued tasks."""
    bt = BackgroundTasks()
    assert len(bt) == 0
    bt.add_task(lambda: None)
    assert len(bt) == 1
    bt.add_task(lambda: None)
    assert len(bt) == 2
    bt.execute()
    assert len(bt) == 0  # cleared after execute
