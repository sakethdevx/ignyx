"""
WebSocket support for Ignyx.
Provides an async WebSocket wrapper that mirrors Starlette's WebSocket API.
"""

import json
from typing import Any, Optional


class WebSocket:
    """
    Async WebSocket wrapper for Ignyx.
    Provides accept(), send_text(), receive_text(), send_json(), receive_json(), close().
    
    The underlying transport is managed by the Rust server via callback functions
    that are injected when the WebSocket connection is established.
    """

    def __init__(self, send_fn, recv_fn, close_fn, accept_fn):
        self._send_fn = send_fn
        self._recv_fn = recv_fn
        self._close_fn = close_fn
        self._accept_fn = accept_fn
        self._accepted = False

    async def accept(self):
        """Accept the WebSocket connection."""
        self._accepted = True
        self._accept_fn()

    async def send_text(self, data: str):
        """Send a text message."""
        self._send_fn(data)

    async def receive_text(self) -> str:
        """Receive a text message. Blocks until a message arrives."""
        return self._recv_fn()

    async def send_json(self, data: Any):
        """Send a JSON message."""
        self._send_fn(json.dumps(data))

    async def receive_json(self) -> Any:
        """Receive and parse a JSON message."""
        text = self._recv_fn()
        return json.loads(text)

    async def close(self, code: int = 1000, reason: str = ""):
        """Close the WebSocket connection."""
        self._close_fn(code)
