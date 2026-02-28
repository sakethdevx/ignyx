"""
Dependency injection system for Ignyx.
Inspired by FastAPI's Depends() pattern.
"""

import concurrent.futures
import inspect
from typing import Any, Callable, Dict, Optional


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


class BackgroundTask:
    """
    A task to be run after the response is sent.

    Usage:
        def send_email(to: str, subject: str):
            # ... send email logic ...
            pass

        @app.post("/register")
        def register(task: BackgroundTask):
            task.add(send_email, "user@example.com", "Welcome!")
            return {"status": "registered"}
    """

    def __init__(self, func: Optional[Callable[..., Any]] = None, *args: Any, **kwargs: Any) -> None:
        "Initialize the background task."
        self._tasks: list[tuple[Callable[..., Any], tuple[Any, ...], Dict[str, Any]]] = []
        if func:
            self.add(func, *args, **kwargs)

    def add(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """Add a background task to be executed after the response is sent."""
        self._tasks.append((func, args, kwargs))

    def execute(self) -> None:
        """Execute all pending background tasks sequentially."""

        for func, args, kwargs in self._tasks:
            try:
                if inspect.iscoroutinefunction(func):
                    import asyncio

                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.run_coroutine_threadsafe(func(*args, **kwargs), loop)
                        else:
                            loop.run_until_complete(func(*args, **kwargs))
                    except RuntimeError:
                        asyncio.run(func(*args, **kwargs))
                else:
                    # Run sync tasks in a thread pool to prevent blocking the event loop
                    import asyncio

                    try:
                        loop = asyncio.get_running_loop()
                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            loop.run_in_executor(pool, lambda: func(*args, **kwargs))
                    except RuntimeError:
                        # Fallback if no loop is running
                        func(*args, **kwargs)
            except Exception as e:
                print(f"Background task error: {e}")

    def __len__(self) -> int:
        "Return the number of pending tasks."
        return len(self._tasks)


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
