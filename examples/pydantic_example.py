from ignyx import Ignyx
from pydantic import BaseModel, ValidationError

app = Ignyx()

class Address(BaseModel):
    city: str
    zip_code: str

class User(BaseModel):
    name: str
    age: int
    address: Address

@app.post("/users")
async def create_user(request):
    try:
        data = request.json()
        user = User(**data)
        return {"status": "success", "user": user.model_dump()}
    except ValidationError as e:
        return {"status": "error", "errors": e.errors()}, 400
