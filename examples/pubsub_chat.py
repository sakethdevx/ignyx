from ignyx import Ignyx

app = Ignyx(title="Ignyx PubSub Chat")

HTML = """
<!DOCTYPE html>
<html>
    <head>
        <title>Ignyx PubSub Chat</title>
        <style>
            body { font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
            #messages { height: 300px; border: 1px solid #ccc; overflow-y: scroll; padding: 10px; margin-bottom: 10px; }
            .msg { margin-bottom: 5px; padding: 5px; background: #f0f0f0; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h1>Ignyx Chat Room</h1>
        <div id="messages"></div>
        <form id="chat-form" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off" placeholder="Type a message..." style="width: 80%; padding: 5px;"/>
            <button type="submit" style="padding: 5px 10px;">Send</button>
        </form>

        <script>
            var ws = new WebSocket("ws://localhost:8000/ws/chat_room_1");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages');
                var message = document.createElement('div');
                message.className = "msg";
                message.textContent = event.data;
                messages.appendChild(message);
                messages.scrollTop = messages.scrollHeight;
            };
            function sendMessage(event) {
                event.preventDefault();
                var input = document.getElementById("messageText");
                if (input.value.trim() !== "") {
                    // Send to the REST endpoint which broadcasts via app.pubsub
                    fetch("/broadcast/chat_room_1", {
                        method: "POST",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify({text: input.value})
                    });
                    input.value = '';
                }
            }
        </script>
    </body>
</html>
"""

@app.get("/")
async def get_chat_ui():
    from ignyx.responses import HTMLResponse
    return HTMLResponse(HTML)

@app.websocket("/ws")
async def websocket_endpoint(ws):
    await ws.accept()
    # In a real app we'd get this from request.query_params or path
    # But since Ignyx WebSocket handler currently doesn't wrap Request
    # and just passes the ws object, we'll sub to a static room for the demo
    await ws.subscribe("chat_room_1")

    try:
        while True:
            await ws.receive_text()
    except Exception:
        pass

@app.post("/broadcast/chat_room_1")
async def broadcast_message(request, body: dict):
    count = app.pubsub.broadcast("chat_room_1", body["text"])
    return {"status": "broadcasted", "subscribers_reached": count}

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
