import asyncio
import json
from typing import Any

import httpx


class TestResponse:
    def __init__(self, status_code: int, body: bytes | str, headers: Any) -> None:
        self.status_code = status_code
        self._body = body
        self.headers = headers
        self.text = body if isinstance(body, str) else body.decode("utf-8", errors="replace")

    def json(self) -> Any:
        return json.loads(self.text)


class TestClient:
    """In-process test client using ASGITransport (no sockets required)."""

    def __init__(self, app: Any) -> None:
        self._asgi_app = app.asgi()
        # Manually invoke startup hooks since ASGITransport in this environment
        # does not manage lifespan events.
        for handler in getattr(app, "_startup_handlers", []):
            if asyncio.iscoroutinefunction(handler):
                asyncio.run(handler())
            else:
                handler()

        transport = httpx.ASGITransport(app=self._asgi_app)
        self._client = httpx.AsyncClient(transport=transport, base_url="http://ignyx.test")

    def _request(self, method: str, path: str, **kwargs: Any) -> TestResponse:
        async def send() -> TestResponse:
            resp = await self._client.request(method, path, **kwargs)
            return TestResponse(resp.status_code, resp.content, resp.headers)

        return asyncio.run(send())

    def get(self, path: str, **kwargs: Any) -> TestResponse:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> TestResponse:
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> TestResponse:
        return self._request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> TestResponse:
        return self._request("DELETE", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> TestResponse:
        return self._request("PATCH", path, **kwargs)

    def __del__(self) -> None:  # pragma: no cover - best-effort cleanup
        try:
            self._client.close()
        except Exception:
            pass
