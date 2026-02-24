from ignyx import Ignyx, Request

app = Ignyx()

@app.post("/users")
def create_user(body: dict, request: Request):
    auth = request.headers.get("authorization")
    if not auth:
        return {"error": "Unauthorized"}, 401
    
    # Check if query parsing worked
    source = request.query_params.get("source", "unknown")
    
    return {"created": body.get("name"), "source": source}, 201

@app.get("/search")
def search(q: str, limit: int = 10):
    return {"query": q, "limit": limit}

@app.get("/protected")
def protected(request: Request):
    token = request.headers.get("authorization")
    if not token:
        return {"error": "Missing token"}, 400
    return {"token": token}, 200

if __name__ == "__main__":
    app.run(port=8000)
