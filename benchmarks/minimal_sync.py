from ignyx import Ignyx
from pydantic import BaseModel

app = Ignyx()

class UserCreate(BaseModel):
    name: str
    age: int

@app.post("/users")
def create_user(body: UserCreate):
    return {"message": f"User {body.name} created"}

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
