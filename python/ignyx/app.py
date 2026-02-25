"""
Ignyx application class — the main entry point for building APIs.
Provides FastAPI-like decorator syntax for defining routes.
Integrates middleware, OpenAPI, dependency injection, and background tasks.
"""

import json
import inspect
from typing import Any, Callable, Dict, List, Optional
from ignyx._core import Server, Request, Response
from ignyx.middleware import Middleware, ErrorHandlerMiddleware
from ignyx.depends import Depends, BackgroundTask, resolve_dependencies
from ignyx.openapi import (
    generate_openapi_schema,
    SWAGGER_UI_HTML,
    REDOC_HTML,
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
        version: str = "0.1.0",
        debug: bool = False,
        description: str = "",
        docs_url: str = "/docs",
        redoc_url: str = "/redoc",
        openapi_url: str = "/openapi.json",
    ):
        self._server = Server()
        self._routes: list[dict] = []
        self._ws_routes: list[dict] = []
        self._middlewares: list[Middleware] = []
        self._dependency_overrides: dict = {}
        self.title = title
        self.version = version
        self.debug = debug
        self.description = description
        self.docs_url = docs_url
        self.redoc_url = redoc_url
        self.openapi_url = openapi_url
        self._openapi_schema: Optional[dict] = None

        # Add default error handler
        self._middlewares.append(ErrorHandlerMiddleware(debug=debug))

    def add_middleware(self, middleware: Middleware):
        """Add a middleware to the application."""
        self._middlewares.insert(0, middleware)  # Prepend so user middleware runs first

    def _add_route(self, method: str, path: str, handler: Callable, **kwargs) -> Callable:
        """Register a route handler."""
        self._server.add_route(method, path, handler)
        self._routes.append({
            "method": method,
            "path": path,
            "handler": handler,
            "name": handler.__name__,
            **kwargs,
        })
        return handler

    def include_router(self, router):
        for method, path, handler in router.routes:
            self._server.add_route(method, path, handler)
            self._routes.append({
                "method": method,
                "path": path,
                "handler": handler,
                "name": handler.__name__,
            })

    def get(self, path: str, **kwargs) -> Callable:
        """Register a GET route."""
        def decorator(func: Callable) -> Callable:
            return self._add_route("GET", path, func, **kwargs)
        return decorator

    def post(self, path: str, **kwargs) -> Callable:
        """Register a POST route."""
        def decorator(func: Callable) -> Callable:
            return self._add_route("POST", path, func, **kwargs)
        return decorator

    def put(self, path: str, **kwargs) -> Callable:
        """Register a PUT route."""
        def decorator(func: Callable) -> Callable:
            return self._add_route("PUT", path, func, **kwargs)
        return decorator

    def delete(self, path: str, **kwargs) -> Callable:
        """Register a DELETE route."""
        def decorator(func: Callable) -> Callable:
            return self._add_route("DELETE", path, func, **kwargs)
        return decorator

    def patch(self, path: str, **kwargs) -> Callable:
        """Register a PATCH route."""
        def decorator(func: Callable) -> Callable:
            return self._add_route("PATCH", path, func, **kwargs)
        return decorator

    def options(self, path: str, **kwargs) -> Callable:
        """Register an OPTIONS route."""
        def decorator(func: Callable) -> Callable:
            return self._add_route("OPTIONS", path, func, **kwargs)
        return decorator

    def websocket(self, path: str) -> Callable:
        """Register a WebSocket route."""
        def decorator(func: Callable) -> Callable:
            self._ws_routes.append({"path": path, "handler": func})
            return func
        return decorator

    def openapi(self) -> dict:
        """Get the OpenAPI schema, generating it if needed."""
        if self._openapi_schema is None:
            self._openapi_schema = generate_openapi_schema(
                title=self.title,
                version=self.version,
                routes=self._routes,
                description=self.description,
            )
        return self._openapi_schema

    def _register_docs_routes(self):
        """Register the OpenAPI, Swagger UI, and ReDoc routes."""
        schema = self.openapi()
        schema_json = json.dumps(schema)

        # OpenAPI JSON endpoint
        def openapi_json():
            return schema

        self._server.add_route("GET", self.openapi_url, openapi_json)

        # Swagger UI
        swagger_html = SWAGGER_UI_HTML.format(
            title=self.title,
            openapi_url=self.openapi_url,
        )

        def swagger_ui():
            return swagger_html

        self._server.add_route("GET", self.docs_url, swagger_ui)

        # ReDoc
        redoc_html = REDOC_HTML.format(
            title=self.title,
            openapi_url=self.openapi_url,
        )

        def redoc():
            return redoc_html

        self._server.add_route("GET", self.redoc_url, redoc)

    def dependency_overrides(self) -> dict:
        """Get the dependency overrides dict (for testing)."""
        return self._dependency_overrides

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the Ignyx server."""
        # Register docs routes before starting
        self._register_docs_routes()

        print(f"🔥 Ignyx v{self.version} — {self.title}", flush=True)
        print(f"   📖 Docs:  http://{host}:{port}{self.docs_url}", flush=True)
        print(f"   📖 ReDoc: http://{host}:{port}{self.redoc_url}", flush=True)
        print(f"   📋 OpenAPI: http://{host}:{port}{self.openapi_url}", flush=True)

        # Build WebSocket route list for Rust
        ws_routes = [(ws["path"], ws["handler"]) for ws in self._ws_routes]
        self._server.run(host, port, self._middlewares, ws_routes)
