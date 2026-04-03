import asyncio
import json
import threading
import time
import urllib.request

import pytest
import websockets
from ignyx import Ignyx


def run_server(app, port):
    app.run(host="127.0.0.1", port=port)

@pytest.mark.asyncio
async def test_pubsub_broadcast():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        s.close()
    except PermissionError:
        pytest.skip("socket bind not permitted in this environment")

    app = Ignyx()

    @app.websocket("/ws")
    async def chat_ws(ws):
        await ws.accept()
        await ws.subscribe("test_room")
        try:
            while True:
                await ws.receive_text()
        except Exception:
            pass

    @app.post("/broadcast")
    async def do_broadcast(request, body: dict):
        count = app.pubsub.broadcast("test_room", body["text"])
        return {"subscribers": count}

    port = 8133
    server_thread = threading.Thread(target=run_server, args=(app, port), daemon=True)
    server_thread.start()

    # Wait for server to boot
    time.sleep(1)

    uri = f"ws://127.0.0.1:{port}/ws"

    async with websockets.connect(uri) as ws1, websockets.connect(uri) as ws2:
        await asyncio.sleep(0.5) # Give subscriptions time to finalize

        # Broadcast via HTTP using standard library urllib
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/broadcast",
            data=json.dumps({"text": "Hello PubSub!"}).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as response:
            assert response.status == 200
            resp_data = json.loads(response.read().decode())
            assert resp_data["subscribers"] == 2

        # Verify both WS clients receive the native Rust broadcast
        msg1 = await asyncio.wait_for(ws1.recv(), timeout=2.0)
        msg2 = await asyncio.wait_for(ws2.recv(), timeout=2.0)

        assert msg1 == "Hello PubSub!"
        assert msg2 == "Hello PubSub!"


