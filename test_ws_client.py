import asyncio
import websockets

async def test():
    async with websockets.connect("ws://localhost:8000/ws") as ws:
        await ws.send("Hello Ignyx!")
        response = await ws.recv()
        print(response)
        assert response == "Echo: Hello Ignyx!", f"Got: {response}"
        print("WebSocket test passed!")

asyncio.run(test())
