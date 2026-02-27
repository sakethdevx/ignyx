from ignyx import Ignyx

app = Ignyx()

@app.middleware
async def custom_logging_middleware(request, call_next):
    print(f"[{request.method}] {request.path}")
    response = await call_next(request)
    print(f"Status: {response.status_code}")
    return response

@app.middleware
async def cors_middleware(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response
