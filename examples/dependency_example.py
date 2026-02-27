from ignyx import Ignyx, Depends

app = Ignyx()

def fake_auth(request):
    token = request.headers.get("Authorization")
    if token and token.startswith("Bearer "):
        return token.split(" ")[1]
    return None

@app.get("/secure")
async def secure_endpoint(request, token=Depends(fake_auth)):
    if not token:
        return {"error": "Unauthorized"}, 401
    return {"message": "Access granted", "token": token}
