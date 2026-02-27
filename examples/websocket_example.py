from ignyx import Ignyx

app = Ignyx()

@app.websocket("/ws")
async def websocket_endpoint(ws):
    await ws.accept()
    while True:
        data = await ws.receive_text()
        if data == "close":
            break
        await ws.send_text(f"Echo: {data}")
