import asyncio
from ignyx import Ignyx

app = Ignyx()

@app.get("/sync")
def sync_handler():
    return {"type": "sync"}

@app.get("/async")
async def async_handler():
    await asyncio.sleep(0)
    return {"type": "async"}

@app.get("/async_no_sleep")
async def async_no_sleep():
    return {"status": "ok", "type": "async_no_sleep"}

@app.get("/users/{id}")
def get_user(id: int):
    return {"id": id}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
