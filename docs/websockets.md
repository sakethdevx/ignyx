# WebSockets
Full bidirectional WebSocket support bridging Rust `tokio-tungstenite` to Python.
```python
@app.websocket("/ws")
async def websocket_endpoint(ws):
    await ws.accept()
    while True:
        data = await ws.receive_text()
        await ws.send_text(f"Echo: {data}")
```
