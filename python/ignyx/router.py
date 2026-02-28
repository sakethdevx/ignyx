from typing import Any, Callable, List, Tuple


class Router:
    """
    A router for organizing and grouping Ignyx API endpoints.

    Usage:
        router = Router(prefix="/api/v1")

        @router.get("/users")
        def get_users():
            ...

        app.include_router(router)
    """

    def __init__(self, prefix: str = "") -> None:
        "Initialize the router with an optional path prefix."
        self.prefix: str = prefix.rstrip("/")
        self.routes: List[Tuple[str, str, Callable[..., Any]]] = []

    def _add_route(self, method: str, path: str, handler: Callable[..., Any]) -> None:
        "Internal method to add a route to the router's list."
        full_path = self.prefix + path
        self.routes.append((method, full_path, handler))

    def get(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a GET route on this router."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._add_route("GET", path, func)
            return func

        return decorator

    def post(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a POST route on this router."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._add_route("POST", path, func)
            return func

        return decorator

    def put(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a PUT route on this router."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._add_route("PUT", path, func)
            return func

        return decorator

    def delete(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a DELETE route on this router."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._add_route("DELETE", path, func)
            return func

        return decorator
