"""
WebSocket support for Ignyx.
Provides an async WebSocket wrapper that mirrors Starlette's WebSocket API.

The Rust server uses bounded channels (capacity=64) for message passing
between the WebSocket I/O tasks and the Python handler.  This provides
built-in backpressure: if the consumer is slow, the producer automatically
awaits until buffer space is available, preventing unbounded memory growth.
"""

import json
from typing import Any, Callable


class WebSocket:
    """
    Async WebSocket wrapper for Ignyx.
    Provides accept(), send_text(), receive_text(), send_json(), receive_json(), close().

    Backpressure is handled transparently by the Rust transport layer:
    - send_text() will block if the outgoing buffer is full (64 messages)
    - receive_text() will block until a message arrives

    The underlying transport is managed by the Rust server via callback functions
    that are injected when the WebSocket connection is established.
    """

    def __init__(self, send_fn: Callable[[str], None], recv_fn: Callable[[], str], close_fn: Callable[[int], None], accept_fn: Callable[[], None]) -> None:
        self._send_fn = send_fn
        self._recv_fn = recv_fn
        self._close_fn = close_fn
        self._accept_fn = accept_fn
        self._accepted = False

    async def accept(self) -> None:
        """Accept the WebSocket connection."""
        self._accepted = True
        self._accept_fn()

    async def send_text(self, data: str) -> None:
        """Send a text message."""
        self._send_fn(data)

    async def receive_text(self) -> str:
        """Receive a text message. Blocks until a message arrives."""
        return str(self._recv_fn())

    async def send_json(self, data: Any) -> None:
        """Send a JSON message."""
        self._send_fn(json.dumps(data))

    async def receive_json(self) -> Any:
        """Receive and parse a JSON message."""
        text = self._recv_fn()
        return json.loads(text)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Close the WebSocket connection."""
        self._close_fn(code)
