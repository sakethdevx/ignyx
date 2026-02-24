"""Honest benchmark app — NO caching, real dynamic handlers."""
from ignyx import Ignyx

app = Ignyx()

@app.get("/plaintext")
def plaintext():
    return "Hello, World!"

@app.get("/json")
def json_response():
    return {"message": "Hello", "framework": "Ignyx"}

@app.get("/users/{id}")
def get_user(id: int):
    return {"user_id": id, "name": f"User {id}"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
