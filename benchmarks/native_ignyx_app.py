from ignyx import Ignyx
from ignyx.middleware import CORSMiddleware
from pydantic import BaseModel

app = Ignyx()
app.add_middleware(CORSMiddleware(allow_origins=['*']))

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
    app.run(host='0.0.0.0', port=8000)
