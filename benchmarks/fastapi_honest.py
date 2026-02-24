"""FastAPI honest benchmark — same 3 endpoints as Ignyx."""
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

app = FastAPI()

@app.get("/plaintext")
def plaintext():
    return PlainTextResponse("Hello, World!")

@app.get("/json")
def json_response():
    return {"message": "Hello", "framework": "FastAPI"}

@app.get("/users/{id}")
def get_user(id: int):
    return {"user_id": id, "name": f"User {id}"}
