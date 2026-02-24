"""FastAPI benchmark comparison app."""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def hello():
    return {"message": "FastAPI is live"}
