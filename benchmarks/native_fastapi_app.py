from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

class User(BaseModel):
    name: str
    age: int

@app.get('/plaintext')
def plaintext():
    return 'Hello, World!'

@app.get('/users/{id}')
def get_user(id: int):
    return {'id': id, 'name': f'User {id}'}

@app.post('/users')
def create_user(body: User):
    return {'name': body.name, 'age': body.age}

if __name__ == "__main__":
    uvicorn.run(app, host='0.0.0.0', port=8001)
