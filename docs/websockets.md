# WebSockets

WebSockets in Ignyx provide full bidirectional, full-duplex communication between the client and the server. Built on top of the high-performance Rust `tokio-tungstenite` library, Ignyx WebSockets are incredibly fast and efficient.

## Overview

Unlike standard HTTP requests, WebSockets maintain a persistent connection, allowing both parties to send data at any time. This is ideal for real-time applications like chat servers, live dashboards, and multiplayer games.

## Basic Example: Echo Server

Creating a WebSocket endpoint is simple. You use the `@app.websocket` decorator and an `async def` function.

```python
from ignyx import Ignyx

app = Ignyx()

@app.websocket("/ws")
async def websocket_endpoint(ws):
    await ws.accept()
    while True:
        try:
            data = await ws.receive_text()
            await ws.send_text(f"Echo: {data}")
        except Exception:
            # Handle disconnection
            break
```

## Advanced Example: Chat Room

You can manage multiple connections using a simple dictionary or list.

```python
from ignyx import Ignyx

app = Ignyx()
connected_clients = set()

@app.websocket("/chat")
async def chat_room(ws):
    await ws.accept()
    connected_clients.add(ws)
    try:
        while True:
            msg = await ws.receive_text()
            # Broadcast to all connected clients
            for client in connected_clients:
                await client.send_text(f"User: {msg}")
    except Exception:
        pass
    finally:
        connected_clients.remove(ws)
```

## Sending JSON

Ignyx makes it easy to work with structured data over WebSockets using JSON.

```python
@app.websocket("/notifications")
async def notifications(ws):
    await ws.accept()
    # Sending a JSON object
    await ws.send_json({"type": "info", "message": "Welcome to the real-time era!"})
    
    # Receiving JSON
    data = await ws.receive_json()
    print(f"Received JSON: {data['content']}")
```

## Closing

You can close a connection gracefully at any time.

```python
@app.websocket("/once")
async def once(ws):
    await ws.accept()
    await ws.send_text("Goodbye!")
    await ws.close(code=1000)
```

## Error Handling

Always wrap your communication loop in a `try/except` block to detect when a client disconnects.

```python
@app.websocket("/safe")
async def safe_ws(ws):
    await ws.accept()
    try:
        while True:
            data = await ws.receive_text()
            # process data
    except Exception as e:
        print(f"Client disconnected or error occurred: {e}")
```

## API Reference

### `ws.accept()`
Accepts the incoming WebSocket connection. This must be called before sending or receiving data.

### `await ws.receive_text()`
Wait for a text message from the client. Returns a `str`.

### `await ws.receive_json()`
Wait for a text message and parse it as JSON. Returns a `dict` or `list`.

### `await ws.send_text(data)`
Send a string message to the client.

### `await ws.send_json(data)`
Serialize the data and send it as a JSON string message.

### `await ws.close(code=1000)`
Close the connection with the specified status code.
