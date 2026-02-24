import asyncio
from pydantic import BaseModel
from ignyx import Ignyx

app = Ignyx()

class UserModel(BaseModel):
    name: str
    age: int

class UpdateUser(BaseModel):
    name: str | None = None
    age: int | None = None

@app.post("/users")
def create_user(body: UserModel):
    return {"name": body.name, "age": body.age}

@app.put("/users/{id}")
def update_user(id: int, body: UpdateUser):
    return {"id": id, "updated": body.model_dump(exclude_none=True)}

@app.get("/async")
async def async_handler():
    await asyncio.sleep(0.01)
    return {"async": True}

@app.get("/async-users/{id}")
async def async_get_user(id: int):
    await asyncio.sleep(0.01)
    return {"id": id, "async": True}

@app.websocket("/ws")
async def websocket_handler(ws):
    await ws.accept()
    while True:
        data = await ws.receive_text()
        await ws.send_text(f"Echo: {data}")

if __name__ == "__main__":
    app.run(port=8000)
