"""
Ignyx application class — the main entry point for building APIs.
Provides FastAPI-like decorator syntax for defining routes.
Integrates middleware, OpenAPI, dependency injection, and background tasks.
"""

import inspect
from typing import Any, Callable, Dict, List, Optional, Type, Union

from ignyx._core import Server
from ignyx.middleware import ErrorHandlerMiddleware, Middleware
from ignyx.openapi import (
    REDOC_HTML,
    SWAGGER_UI_HTML,
    generate_openapi_schema,
)


class Ignyx:
    """
    The main Ignyx application.

    Usage:
        from ignyx import Ignyx

        app = Ignyx()

        @app.get("/")
        def hello():
            return {"message": "Ignyx is live"}

        app.run(host="0.0.0.0", port=8000)
    """

    def __init__(
        self,
        title: str = "Ignyx",
        version: str = "2.1.3",
        debug: bool = False,
        description: str = "",
        docs_url: str = "/docs",
        redoc_url: str = "/redoc",
        openapi_url: str = "/openapi.json",
    ) -> None:
        """Initialize the Ignyx application."""
        self._server: Server = Server()
        self._routes: List[Dict[str, Any]] = []
        self._ws_routes: List[Dict[str, Any]] = []
        self._middlewares: List[Middleware] = []
        self._dependency_overrides: Dict[Callable[..., Any], Any] = {}
        self.title: str = title
        self.version: str = version
        self.debug: bool = debug
        self.description: str = description
        self.docs_url: str = docs_url
        self.redoc_url: str = redoc_url
        self.openapi_url: str = openapi_url
        self._openapi_schema: Optional[Dict[str, Any]] = None
        self._exception_handlers: Dict[Union[int, Type[Exception]], Callable[..., Any]] = {}
        self._startup_handlers: List[Callable[..., Any]] = []
        self._shutdown_handlers: List[Callable[..., Any]] = []

        from types import SimpleNamespace

        self.state: SimpleNamespace = SimpleNamespace()

        # Add default error handler
        self._middlewares.append(ErrorHandlerMiddleware(debug=debug))

    def exception_handler(
        self, status_code_or_exc: Union[int, Type[Exception]]
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator to register a custom exception handler."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._exception_handlers[status_code_or_exc] = func
            return func

        return decorator

    def on_startup(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Register a function to run before the server starts."""
        self._startup_handlers.append(func)
        return func

    def on_shutdown(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Register a function to run when the server shuts down."""
        self._shutdown_handlers.append(func)
        return func

    def _handle_exception(self, request: Any, exc: Optional[Exception], status_code: int) -> Any:
        "Internal exception dispatcher."
        # Check exception type
        for exc_type, handler in self._exception_handlers.items():
            if isinstance(exc_type, type) and isinstance(exc, exc_type):
                return handler(request, exc)
        # Check status code
        if status_code in self._exception_handlers:
            return self._exception_handlers[status_code](request, exc)
        return None

    def _create_dispatch(self, handler: Callable[..., Any]) -> Callable[..., Any]:
        "Create a dispatch wrapper for sync or async handlers."
        from functools import wraps

        if inspect.iscoroutinefunction(handler):

            @wraps(handler)
            async def async_dispatch(*args: Any, **kw: Any) -> Any:
                request = kw.get("request") or (args[0] if args else None)
                try:
                    res = await handler(*args, **kw)
                    if hasattr(res, "status_code"):
                        handled = self._handle_exception(request, None, res.status_code)
                        if handled:
                            return handled
                    return res
                except Exception as exc:
                    status_code = getattr(exc, "status_code", 500)
                    handled = self._handle_exception(request, exc, status_code)
                    if handled:
                        return handled
                    raise exc

            return async_dispatch
        else:

            @wraps(handler)
            def sync_dispatch(*args: Any, **kw: Any) -> Any:
                request = kw.get("request") or (args[0] if args else None)
                try:
                    res = handler(*args, **kw)
                    if hasattr(res, "status_code"):
                        handled = self._handle_exception(request, None, res.status_code)
                        if handled:
                            return handled
                    return res
                except Exception as exc:
                    status_code = getattr(exc, "status_code", 500)
                    handled = self._handle_exception(request, exc, status_code)
                    if handled:
                        return handled
                    raise exc

            return sync_dispatch

    def add_middleware(self, middleware: Middleware) -> None:
        """Add a middleware to the application."""
        self._middlewares.append(middleware)

    def _add_route(
        self, method: str, path: str, handler: Callable[..., Any], **kwargs: Any
    ) -> Callable[..., Any]:
        """Register a route handler internally."""
        dispatch = self._create_dispatch(handler)
        self._server.add_route(method, path, dispatch)
        self._routes.append(
            {
                "method": method,
                "path": path,
                "handler": handler,
                "name": getattr(handler, "__name__", "unknown"),
                **kwargs,
            }
        )
        if method != "OPTIONS" and not any(
            r["path"] == path and r["method"] == "OPTIONS" for r in self._routes
        ):
            self._server.add_route("OPTIONS", path, self._create_dispatch(lambda request: ""))
            self._routes.append(
                {"method": "OPTIONS", "path": path, "handler": lambda req: "", "name": "options"}
            )
        return handler

    def include_router(self, router: Any) -> None:
        """Include routes from a Router instance."""
        for method, path, handler, tags in router.routes:
            dispatch = self._create_dispatch(handler)
            self._server.add_route(method, path, dispatch)
            self._routes.append(
                {
                    "method": method,
                    "path": path,
                    "handler": handler,
                    "name": getattr(handler, "__name__", "unknown"),
                    "tags": tags,
                }
            )

    def get(
        self, path: str, tags: Optional[List[str]] = None, **kwargs: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a GET route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return self._add_route("GET", path, func, tags=tags, **kwargs)

        return decorator

    def post(
        self, path: str, tags: Optional[List[str]] = None, **kwargs: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a POST route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return self._add_route("POST", path, func, tags=tags, **kwargs)

        return decorator

    def put(
        self, path: str, tags: Optional[List[str]] = None, **kwargs: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a PUT route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return self._add_route("PUT", path, func, tags=tags, **kwargs)

        return decorator

    def delete(
        self, path: str, tags: Optional[List[str]] = None, **kwargs: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a DELETE route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return self._add_route("DELETE", path, func, tags=tags, **kwargs)

        return decorator

    def patch(
        self, path: str, tags: Optional[List[str]] = None, **kwargs: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a PATCH route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return self._add_route("PATCH", path, func, tags=tags, **kwargs)

        return decorator

    def options(
        self, path: str, tags: Optional[List[str]] = None, **kwargs: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register an OPTIONS route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return self._add_route("OPTIONS", path, func, tags=tags, **kwargs)

        return decorator

    def websocket(self, path: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a WebSocket route."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._ws_routes.append({"path": path, "handler": func})
            return func

        return decorator

    def mount(self, path: str, app: Callable[..., Any]) -> None:
        """Mount a sub-application or static files handler."""
        mount_path = path.rstrip("/")

        def static_handler(request: Any, file_path: str = "") -> Any:
            return app(file_path)

        # Register a catch-all route for the mounted path
        self._server.add_route("GET", mount_path + "/{*file_path}", static_handler)

    def openapi(self) -> Dict[str, Any]:
        """Get the OpenAPI schema, generating it if needed."""
        if self._openapi_schema is None:
            self._openapi_schema = generate_openapi_schema(
                title=self.title,
                version=self.version,
                routes=self._routes,
                description=self.description,
            )
        return self._openapi_schema

    def _register_docs_routes(self) -> None:
        """Register the OpenAPI, Swagger UI, and ReDoc routes."""
        schema = self.openapi()

        # OpenAPI JSON endpoint
        def openapi_json() -> Dict[str, Any]:
            return schema

        self._server.add_route("GET", self.openapi_url, openapi_json)

        # Swagger UI
        swagger_html = SWAGGER_UI_HTML.format(
            title=self.title,
            openapi_url=self.openapi_url,
        )

        def swagger_ui() -> str:
            return swagger_html

        self._server.add_route("GET", self.docs_url, swagger_ui)

        # ReDoc
        redoc_html = REDOC_HTML.format(
            title=self.title,
            openapi_url=self.openapi_url,
        )

        def redoc() -> str:
            return redoc_html

        self._server.add_route("GET", self.redoc_url, redoc)

    def dependency_overrides(self) -> Dict[Callable[..., Any], Any]:
        """Get the dependency overrides dict (for testing)."""
        return self._dependency_overrides

    def run(self, host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> None:
        """Start the Ignyx server."""
        if reload:
            from ignyx.reload import run_with_reload
            import inspect
            import sys

            frame = inspect.stack()[1]
            module = inspect.getmodule(frame[0])
            mod_name = module.__name__ if module else "__main__"
            run_with_reload(mod_name, host=host, port=port)
            return

        # Register docs routes before starting
        self._register_docs_routes()

        print(f"🔥 Ignyx v{self.version} — {self.title}", flush=True)
        print(f"   📖 Docs:  http://{host}:{port}{self.docs_url}", flush=True)
        print(f"   📖 ReDoc: http://{host}:{port}{self.redoc_url}", flush=True)
        print(f"   📋 OpenAPI: http://{host}:{port}{self.openapi_url}", flush=True)

        # Build WebSocket route list for Rust
        ws_routes = [(ws["path"], ws["handler"]) for ws in self._ws_routes]

        # Pass 404 handler to Rust
        def not_found_handler(request: Any) -> Any:
            res = self._handle_exception(request, None, 404)
            if res:
                return res
            from ignyx.responses import JSONResponse

            return JSONResponse(
                {"error": "Not Found", "detail": "No route found"}, status_code=404
            )

        import asyncio

        for handler in self._startup_handlers:
            if asyncio.iscoroutinefunction(handler):
                asyncio.run(handler())
            else:
                handler()

        self._server.run(
            host, port, self._middlewares, ws_routes, not_found_handler, self._shutdown_handlers
        )
