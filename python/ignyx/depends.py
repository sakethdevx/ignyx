"""
Dependency injection system for Ignyx.
Inspired by FastAPI's Depends() pattern.

Also contains the BackgroundTasks engine — the high-performance fire-and-forget
task scheduler that runs Python callables after the HTTP response has been sent,
without blocking the Tokio event loop.
"""

import asyncio
import concurrent.futures
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Shared thread-pool used by all BackgroundTasks instances.
# Tasks are submitted here so they truly run concurrently in OS threads.
_BG_EXECUTOR: concurrent.futures.ThreadPoolExecutor = concurrent.futures.ThreadPoolExecutor(
    max_workers=10,
    thread_name_prefix="ignyx-bg",
)


class Depends:
    """
    Declare a dependency for a route handler.

    Usage:
        def get_db():
            db = Database()
            try:
                yield db
            finally:
                db.close()

        @app.get("/users")
        def get_users(db = Depends(get_db)):
            return db.query("SELECT * FROM users")
    """

    def __init__(self, dependency: Callable[..., Any], use_cache: bool = True) -> None:
        "Initialize the dependency."
        self.dependency = dependency
        self.use_cache = use_cache

    def __repr__(self) -> str:
        "Simple string representation."
        return f"Depends({self.dependency.__name__})"


class BackgroundTasks:
    """
    High-performance fire-and-forget background task scheduler.

    Declare ``tasks: BackgroundTasks`` as a route parameter and Ignyx will
    inject a fresh instance.  Add as many callables as you like — they are
    submitted to a shared ``ThreadPoolExecutor`` (10 workers by default)
    **after** the HTTP response body has been flushed to the client, so the
    caller never waits.

    Async callables are supported: they are scheduled on the running event
    loop via ``asyncio.run_coroutine_threadsafe``.

    Usage::

        from ignyx import Ignyx
        from ignyx.depends import BackgroundTasks

        app = Ignyx()

        def send_welcome_email(to: str) -> None:
            # heavy I/O — will not block the HTTP response
            import time; time.sleep(2)
            print(f"Email sent to {to}")

        @app.post("/register")
        def register(body: dict, tasks: BackgroundTasks):
            tasks.add_task(send_welcome_email, body["email"])
            return {"status": "registered"}

    """

    def __init__(self) -> None:
        "Create an empty BackgroundTasks queue."
        self._queue: List[Tuple[Callable[..., Any], Tuple[Any, ...], Dict[str, Any]]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_task(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """
        Enqueue *func* to be called with *args* and *kwargs* after the
        current response has been sent.

        Both sync and async callables are accepted.
        """
        self._queue.append((func, args, kwargs))

    # Backwards-compat alias used by BackgroundTask (singular)
    def add(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """Alias for :meth:`add_task`."""
        self.add_task(func, *args, **kwargs)

    # ------------------------------------------------------------------
    # Execution helpers
    # ------------------------------------------------------------------

    def _submit_sync(self, func: Callable[..., Any], args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> None:
        """Submit a synchronous callable to the shared thread-pool."""
        def _run() -> None:
            try:
                func(*args, **kwargs)
            except Exception as exc:
                logger.error("BackgroundTask sync error: %s", exc, exc_info=True)

        _BG_EXECUTOR.submit(_run)

    def _submit_async(self, func: Callable[..., Any], args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> None:
        """Schedule an async callable via the running event loop."""
        async def _coro() -> None:
            try:
                await func(*args, **kwargs)
            except Exception as exc:
                logger.error("BackgroundTask async error: %s", exc, exc_info=True)

        try:
            loop = asyncio.get_running_loop()
            asyncio.run_coroutine_threadsafe(_coro(), loop)
        except RuntimeError:
            # No running loop — fall back to a new event-loop in a thread
            def _run_in_thread() -> None:
                asyncio.run(_coro())
            _BG_EXECUTOR.submit(_run_in_thread)

    def execute(self) -> None:
        """
        Fire all queued tasks.

        Called by Ignyx's dispatch layer immediately after the response is
        serialised but before the connection is released, so callers receive
        their HTTP response without waiting for any task to complete.
        """
        for func, args, kwargs in self._queue:
            if inspect.iscoroutinefunction(func):
                self._submit_async(func, args, kwargs)
            else:
                self._submit_sync(func, args, kwargs)
        self._queue.clear()

    def __len__(self) -> int:
        "Return the number of pending tasks."
        return len(self._queue)


class BackgroundTask(BackgroundTasks):
    """
    Single-task convenience wrapper — backwards-compatible with the v2.4 API.

    Prefer :class:`BackgroundTasks` for new code.

    Usage::

        @app.post("/notify")
        def notify(task: BackgroundTask):
            task.add(send_email, "user@example.com", "Hello!")
            return {"status": "ok"}
    """

    def __init__(self, func: Optional[Callable[..., Any]] = None, *args: Any, **kwargs: Any) -> None:
        "Optionally wrap a single callable at construction time."
        super().__init__()
        if func is not None:
            self.add_task(func, *args, **kwargs)


def resolve_dependencies(
    handler: Callable[..., Any],
    request: Any = None,
    overrides: Optional[Dict[Callable[..., Any], Any]] = None,
    cache: Optional[Dict[Callable[..., Any], Any]] = None,
) -> Dict[str, Any]:
    """
    Resolve dependencies declared in a handler's signature.
    Returns a dict of resolved dependency values.
    """
    overrides = overrides or {}
    if cache is None:
        cache = {}

    sig = inspect.signature(handler)
    resolved: Dict[str, Any] = {}

    for name, param in sig.parameters.items():
        if isinstance(param.default, Depends):
            dep = param.default
            func = dep.dependency

            if func in overrides:
                resolved[name] = overrides[func]
                continue

            if dep.use_cache and func in cache:
                resolved[name] = cache[func]
                continue

            # Resolve inner dependencies (recursion)
            inner_deps = resolve_dependencies(func, request, overrides, cache)

            # Call the dependency with resolved inner dependencies and optional request
            dep_sig = inspect.signature(func)
            kwargs = inner_deps.copy()
            if "request" in dep_sig.parameters and "request" not in kwargs:
                kwargs["request"] = request

            result = func(**kwargs)
            if inspect.isgenerator(result):
                # Generator-based dependency (with cleanup)
                value = next(result)
                # Note: Cleanup (yield) is not yet supported in this simple sync implementation
            else:
                value = result

            if dep.use_cache:
                cache[func] = value
            resolved[name] = value

    return resolved
