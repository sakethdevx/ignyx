"""
AWS Lambda adapter for Ignyx.

Provides a zero-config bridge from API Gateway / Lambda HTTP events to the
Ignyx ASGI app, similar to Mangum. Intended usage inside ``lambda_handler``:

    from ignyx import Ignyx
    from ignyx.serverless import IgnyxLambda

    app = Ignyx()

    @app.get("/")
    def hello():
        return {"message": "Ignyx on Lambda"}

    handler = IgnyxLambda(app)

    def lambda_handler(event, context):
        return handler(event, context)
"""

from __future__ import annotations

import asyncio
import base64
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import urlencode

from ignyx.asgi import IgnyxASGI


class IgnyxLambda:
    """Lightweight AWS Lambda adapter for Ignyx ASGI apps."""

    def __init__(self, app: Any, binary_media_types: Iterable[str] | None = None) -> None:
        self._asgi_app = app.asgi() if hasattr(app, "asgi") else IgnyxASGI(app)
        self._binary_media_types = {mt.lower() for mt in (binary_media_types or set())}

    # ── Public entry point -------------------------------------------------
    def __call__(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Handle a single Lambda invocation."""
        return asyncio.run(self._invoke(event, context))

    # ── Event → scope helpers ---------------------------------------------
    @staticmethod
    def _coalesce_headers(event: Dict[str, Any]) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        multi = event.get("multiValueHeaders") or {}
        if multi:
            for key, values in multi.items():
                if isinstance(values, list) and values:
                    headers[key.lower()] = ", ".join(str(v) for v in values if v is not None)
                elif values is not None:
                    headers[key.lower()] = str(values)
        else:
            for key, value in (event.get("headers") or {}).items():
                if value is not None:
                    headers[key.lower()] = str(value)
        return headers

    @staticmethod
    def _encode_query(event: Dict[str, Any]) -> str:
        if event.get("rawQueryString") is not None:
            return str(event.get("rawQueryString", ""))

        multi_qs = event.get("multiValueQueryStringParameters")
        if multi_qs:
            pairs: List[Tuple[str, Any]] = []
            for key, values in multi_qs.items():
                if isinstance(values, list):
                    for v in values:
                        pairs.append((key, "" if v is None else v))
                else:
                    pairs.append((key, "" if values is None else values))
            return urlencode(pairs, doseq=True)

        qs = event.get("queryStringParameters") or {}
        if qs:
            return urlencode({k: "" if v is None else v for k, v in qs.items()}, doseq=True)
        return ""

    def _event_to_scope(self, event: Dict[str, Any]) -> Tuple[Dict[str, Any], bytes]:
        headers = self._coalesce_headers(event)

        if "cookies" in event and "cookie" not in headers:
            headers["cookie"] = "; ".join(event.get("cookies", []))

        method = (
            event.get("requestContext", {}).get("http", {}).get("method")
            or event.get("httpMethod")
            or "GET"
        ).upper()

        path = event.get("rawPath") or event.get("path") or "/"
        query_string = self._encode_query(event).encode()

        body = event.get("body", "") or ""
        body_bytes = (
            base64.b64decode(body) if event.get("isBase64Encoded") else str(body).encode()
        )

        server_name = headers.get("host") or event.get("requestContext", {}).get("domainName")
        server = (server_name or "lambda", 443 if headers.get("x-forwarded-proto") == "https" else 80)

        client_ip = (
            event.get("requestContext", {})
            .get("http", {})
            .get("sourceIp", event.get("requestContext", {}).get("identity", {}).get("sourceIp"))
        )
        client = (client_ip or "lambda", 0)

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "path": path,
            "raw_path": path.encode(),
            "query_string": query_string,
            "headers": [(k.encode(), str(v).encode()) for k, v in headers.items()],
            "server": server,
            "client": client,
        }
        return scope, body_bytes

    # ── ASGI invocation ----------------------------------------------------
    async def _invoke(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        scope, body_bytes = self._event_to_scope(event)
        response: Dict[str, Any] = {"status": 200, "headers": [], "body": bytearray()}

        messages = [
            {"type": "http.request", "body": body_bytes, "more_body": False},
        ]

        async def receive() -> Dict[str, Any]:
            return messages.pop(0) if messages else {"type": "http.disconnect"}

        async def send(message: Dict[str, Any]) -> None:
            msg_type = message.get("type")
            if msg_type == "http.response.start":
                response["status"] = message.get("status", 200)
                response["headers"] = message.get("headers", [])
            elif msg_type == "http.response.body":
                chunk = message.get("body", b"") or b""
                response["body"].extend(chunk)

        await self._asgi_app(scope, receive, send)

        headers: Dict[str, str] = {}
        multi_headers: Dict[str, List[str]] = {}

        for raw_key, raw_val in response.get("headers", []):
            key = raw_key.decode("latin-1")
            val = raw_val.decode("latin-1")
            if key in headers:
                multi_headers.setdefault(key, [headers[key]]).append(val)
            else:
                headers[key] = val

        body_bytes_out = bytes(response["body"])
        content_type = headers.get("content-type", "")
        is_base64 = self._should_base64(content_type, body_bytes_out)

        if is_base64:
            body_str = base64.b64encode(body_bytes_out).decode()
        else:
            body_str = body_bytes_out.decode("utf-8", errors="replace")

        payload: Dict[str, Any] = {
            "statusCode": response.get("status", 200),
            "headers": headers,
            "body": body_str,
            "isBase64Encoded": is_base64,
        }
        if multi_headers:
            payload["multiValueHeaders"] = multi_headers
        return payload

    # ── Binary detection ----------------------------------------------------
    def _should_base64(self, content_type: str, body: bytes) -> bool:
        if not body:
            return False

        if content_type:
            lowered = content_type.lower()
            if lowered in self._binary_media_types:
                return True
            if lowered.startswith("text/"):
                return False
            if any(lowered.startswith(prefix) for prefix in ("application/json", "application/xml", "application/javascript")):
                return False

        try:
            body.decode("utf-8")
            return False
        except UnicodeDecodeError:
            return True

