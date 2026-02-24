"""
Dependency injection system for Ignyx.
Inspired by FastAPI's Depends() pattern.
"""

from typing import Any, Callable, Optional
import inspect


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

    def __init__(self, dependency: Callable, use_cache: bool = True):
        self.dependency = dependency
        self.use_cache = use_cache

    def __repr__(self):
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

    def __init__(self):
        self._tasks: list[tuple[Callable, tuple, dict]] = []

    def add(self, func: Callable, *args: Any, **kwargs: Any):
        """Add a background task to be executed after the response is sent."""
        self._tasks.append((func, args, kwargs))

    def execute(self):
        """Execute all pending background tasks sequentially via synchronous thread execution."""
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
                    func(*args, **kwargs)
            except Exception as e:
                print(f"Background task error: {e}")

    def __len__(self):
        return len(self._tasks)


def resolve_dependencies(handler: Callable, overrides: dict = None) -> dict:
    """
    Resolve dependencies declared in a handler's signature.
    Returns a dict of resolved dependency values.
    """
    overrides = overrides or {}
    sig = inspect.signature(handler)
    resolved = {}

    for name, param in sig.parameters.items():
        if isinstance(param.default, Depends):
            dep = param.default
            if dep.dependency in overrides:
                resolved[name] = overrides[dep.dependency]
            else:
                # Call the dependency
                result = dep.dependency()
                if inspect.isgenerator(result):
                    # Generator-based dependency (with cleanup)
                    resolved[name] = next(result)
                else:
                    resolved[name] = result
        elif param.default is inspect.Parameter.empty:
            # Required parameter without dependency — skip (will be filled from request)
            pass

    return resolved
