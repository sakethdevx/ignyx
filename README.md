<p align="center">
  <img src="https://raw.githubusercontent.com/sakethdevx/ignyx/main/docs/assets/ignyx-logo.png" alt="Ignyx Logo" width="200" onerror="this.src='https://placehold.co/400x150/1e1e2e/e0e0e0?text=Ignyx&font=lora'">
  <br>
  <em>Ignite your API. Built in Rust, runs in Python.</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/ignyx/">
    <img src="https://badge.fury.io/py/ignyx.svg" alt="PyPI version">
  </a>
  <a href="https://pepy.tech/projects/ignyx">
    <img src="https://static.pepy.tech/personalized-badge/ignyx?period=total&units=INTERNATIONAL_SYSTEM&left_color=grey&right_color=brightgreen&left_text=Downloads" alt="Downloads">
  </a>
  <a href="https://github.com/sakethdevx/ignyx/actions">
    <img src="https://github.com/sakethdevx/ignyx/actions/workflows/CI.yml/badge.svg" alt="CI status">
  </a>
  <a href="https://pypi.org/project/ignyx/">
    <img src="https://img.shields.io/pypi/pyversions/ignyx" alt="Python versions">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
  </a>
  <a href="https://sakethdevx.github.io/ignyx">
    <img src="https://img.shields.io/badge/docs-online-blue" alt="Docs">
  </a>
</p>

## Description

Ignyx is a next-generation Python web framework engineered for maximum throughput, utilizing a Rust-powered HTTP core built on Hyper and Tokio. It provides a familiar, FastAPI-like decorator syntax, allowing developers to build high-performance APIs with zero learning curve. In honest benchmarks, Ignyx operates 8-9x faster than standard Python async frameworks. It integrates seamlessly with the modern Python ecosystem, featuring full async/await capability, Pydantic v2 validation, WebSockets, and dependency injection.

## Features

- Blazing fast (8-9x FastAPI)
- Owns full HTTP pipeline — no ASGI overhead
- Native async/await support
- Pydantic v2 validation
- Dependency injection (Depends pattern)
- WebSocket support
- Modular routing with Router + prefix
- `py.typed` for full IDE autocompletion

## Benchmark

*Apple M2, `wrk -t4 -c100 -d10s`*

| Endpoint           | Ignyx        | FastAPI     | Speedup |
| ------------------ | ------------ | ----------- | ------- |
| `/plaintext`       | 53,886 req/s | 6,193 req/s | 🔥 8.70x |
| `/users/{id}`      | 48,988 req/s | 5,597 req/s | 🔥 8.75x |
| `/users` (POST JSON)| 44,178 req/s | 5,200 req/s | 🔥 8.49x |

*Note: FastAPI tested with Uvicorn single worker — standard config.*

## Installation

```bash
pip install ignyx==2.1.0
```
Or with `uv`:
```bash
uv add ignyx
```

## Quickstart

```python
from ignyx import Ignyx

app = Ignyx()

@app.get("/")
async def root(request):
    return {"message": "Hello from Ignyx!"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

## Feature Examples

<details>
<summary><b>Pydantic Validation</b></summary>

```python
from ignyx import Ignyx
from pydantic import BaseModel, ValidationError

app = Ignyx()

class User(BaseModel):
    name: str
    age: int

@app.post("/users")
async def create_user(request):
    try:
        user = User(**request.json())
        return {"status": "success", "data": user.model_dump()}
    except ValidationError as e:
        return {"error": e.errors()}, 400
```
</details>

<details>
<summary><b>Path + Query Parameters</b></summary>

```python
from ignyx import Ignyx

app = Ignyx()

@app.get("/users/{id}")
async def get_user(request, id: int):
    format_type = request.query.get("format", "json")
    return {"id": id, "format": format_type}
```
</details>

<details>
<summary><b>Dependency Injection</b></summary>

```python
from ignyx import Ignyx, Depends

app = Ignyx()

def get_token(request):
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    return None

@app.get("/secure")
async def secure_route(request, token=Depends(get_token)):
    if not token:
        return {"error": "Unauthorized"}, 401
    return {"message": "Access granted", "token": token}
```
</details>

<details>
<summary><b>Middleware</b></summary>

```python
from ignyx import Ignyx

app = Ignyx()

@app.middleware
async def cors_middleware(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response
```
</details>

<details>
<summary><b>WebSockets</b></summary>

```python
from ignyx import Ignyx

app = Ignyx()

@app.websocket("/echo")
async def echo_server(ws):
    await ws.accept()
    while True:
        data = await ws.receive_text()
        if data == "close":
            break
        await ws.send_text(f"Echo: {data}")
```
</details>

<details>
<summary><b>Modular Routing</b></summary>

```python
from ignyx import Ignyx, Router

app = Ignyx()
api_router = Router(prefix="/api/v1")

@api_router.get("/status")
async def status(request):
    return {"status": "operational"}

app.include_router(api_router)
```
</details>

## Comparison vs FastAPI

| Feature                | Ignyx | FastAPI |
| ---------------------- | ----- | ------- |
| Pydantic v2 validation | ✅    | ✅      |
| Async/Await            | ✅    | ✅      |
| Dependency Injection   | ✅    | ✅      |
| WebSockets             | ✅    | ✅      |
| Modular Routers        | ✅    | ✅      |
| Performance (req/s)    | ~50k  | ~6k     |
| ASGI overhead          | ❌ None | ✅ Yes |
| TestClient             | ✅ | ✅     |
| Static file serving    | ✅ | ✅     |
| Lifespan events        | ✅ | ✅     |
| Exception handlers     | ✅    | ✅      |

## Current Limitations

- Hot reloading not yet implemented
- OpenAPI schema is basic (no Pydantic response schemas yet)

These are all on the roadmap and will ship in upcoming releases.

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on how to set up your development environment.

## Deployment Note

Ignyx manages its own Tokio runtime. No Uvicorn or Gunicorn needed. Just `python app.py`.

## License

This project is licensed under the [MIT License](LICENSE).