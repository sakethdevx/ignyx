# 🔥 Ignyx

> **Ignite your API. Built in Rust, runs in Python.**

[![PyPI version](https://badge.fury.io/py/ignyx.svg)](https://badge.fury.io/py/ignyx)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

Ignyx is a Rust-powered Python web framework delivering **8x faster performance than FastAPI** — with a full production feature set. Not a stripped-down benchmark. Not a hello world trick. Real dynamic routing, real middleware, real Pydantic validation, measured side by side under identical conditions.

```bash
pip install ignyx
```

---

## ⚡️ The Benchmark: ~8.7x Faster than FastAPI
Tested on MacBook Air M2 (native ARM64). Both frameworks configured identically (CORS + Pydantic + dynamic routing).

| Endpoint | Ignyx | FastAPI | Speedup | Latency |
| :--- | :--- | :--- | :--- | :--- |
| `/plaintext` | **53,886 req/s** | 6,193 req/s | **8.70x** | **2.22ms** |
| `/users/{id}` | **48,988 req/s** | 5,597 req/s | **8.75x** | **2.39ms** |
| `/users` (JSON) | **44,178 req/s** | 5,200 req/s | **8.49x** | **2.61ms** |

*(Tool: `wrk -t4 -c100 -d10s`)*

> Full methodology and raw output in [BENCHMARK.md](BENCHMARK.md)

---

## Why Ignyx is faster

- **Hyper + Tokio** instead of Uvicorn — Rust async HTTP vs Python async HTTP
- **matchit radix tree router** — O(log n) route matching vs linear matching
- **Zero-copy lazy allocation** — headers, body, query params only allocated when the handler actually needs them
- **No ASGI overhead** — direct Rust HTTP → Python handler → Rust response, bypassing the ASGI protocol entirely
- **Signature caching** — handler parameter inspection happens once at registration, never per request

---

## Quick Start

```bash
pip install ignyx
```

```python
from ignyx import Ignyx
from pydantic import BaseModel

app = Ignyx()

class User(BaseModel):
    name: str
    age: int

@app.get("/")
def hello():
    return {"message": "Ignyx is live"}

@app.get("/users/{id}")
def get_user(id: int):
    return {"id": id}

@app.post("/users")
def create_user(body: User):
    return {"name": body.name, "age": body.age}

app.run(host="0.0.0.0", port=8000)
```

One character swap from FastAPI. Your app runs 8x faster.

---

## Features

| Feature | Status |
|---------|--------|
| Dynamic routing with path params | ✅ |
| POST body parsing | ✅ |
| Query parameters | ✅ |
| Case-insensitive headers | ✅ |
| Custom status codes & response headers | ✅ |
| CORS middleware | ✅ |
| Dependency injection (`Depends`) | ✅ |
| Background tasks | ✅ |
| Pydantic v2 validation + 422 errors | ✅ |
| Async handler support (`async def`) | ✅ |
| WebSockets | ✅ |
| OpenAPI 3.0 schema auto-generation | ✅ |
| Swagger UI (`/docs`) | ✅ |
| ReDoc (`/redoc`) | ✅ |

---

## Usage Examples

### Path Parameters

```python
@app.get("/users/{id}")
def get_user(id: int):
    return {"id": id, "name": f"User {id}"}
```

### Query Parameters

```python
@app.get("/search")
def search(q: str, limit: int = 10):
    return {"query": q, "limit": limit}
```

### Request Headers

```python
from ignyx.request import Request

@app.get("/protected")
def protected(request: Request):
    token = request.headers.get("Authorization")
    if not token:
        return {"error": "Unauthorized"}, 401
    return {"token": token}, 200
```

### Pydantic v2 Validation

```python
from pydantic import BaseModel

class User(BaseModel):
    name: str
    age: int

@app.post("/users")
def create_user(body: User):
    return {"name": body.name, "age": body.age}

# Invalid requests automatically return 422 with structured Pydantic errors
```

### Middleware

```python
from ignyx.middleware import CORSMiddleware

app.add_middleware(CORSMiddleware(allow_origins=["*"]))
```

### Dependency Injection

```python
from ignyx.depends import Depends

def get_db():
    return {"connection": "active"}

@app.get("/users")
def get_users(db=Depends(get_db)):
    return {"db": db}
```

### Background Tasks

```python
from ignyx.depends import BackgroundTask

def send_email(address: str):
    print(f"Sending email to {address}")

@app.post("/register")
def register(task: BackgroundTask):
    task.add(send_email, "user@example.com")
    return {"status": "registered"}
```

### WebSockets

```python
@app.websocket("/ws")
async def websocket_handler(ws):
    await ws.accept()
    while True:
        data = await ws.receive_text()
        await ws.send_text(f"Echo: {data}")
```

### Async Handlers

```python
import asyncio

@app.get("/async")
async def async_handler():
    await asyncio.sleep(0.01)
    return {"async": True}
```

### Custom Status Codes

```python
@app.get("/users/{id}")
def get_user(id: int):
    if id == 0:
        return {"error": "Not found"}, 404
    return {"id": id}, 200
```

---

## API Documentation

Ignyx auto-generates OpenAPI 3.0 docs from your type hints.

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Rust + Python |
| Python Bindings | PyO3 + maturin |
| Async Runtime | Tokio |
| HTTP Layer | Hyper |
| Router | matchit (radix tree) |
| Serialization | serde + serde_json |
| Validation | Pydantic v2 |

---

## Platform Support

| Platform | Status |
|----------|--------|
| macOS ARM64 (M1/M2/M3) | ✅ Native |
| macOS x86_64 | ✅ Supported |
| Linux x86_64 | 🔜 Coming in v0.2.0 |
| Windows | 🔜 Coming in v0.2.0 |

---

## Honest Caveats (v0.1.0)

This is an early release. Here's what you should know before using it in production:

- Currently tested on macOS only — Linux and Windows wheels coming in v0.2.0
- Async handlers use `asyncio.run()` per call — a persistent event loop reuse is planned for v0.2.0
- No file upload support yet
- No cookie/session handling yet
- No production deployment guide yet (Docker, Nginx, Gunicorn)
- Zero community yet — you're an early adopter

The core Rust engine is solid. The Python API layer is functional but not battle-tested.

---

## Roadmap

- [ ] Linux + Windows wheels (v0.2.0)
- [ ] GitHub Actions CI for multi-platform builds
- [ ] Native async event loop reuse
- [ ] File uploads (`multipart/form-data`)
- [ ] Cookie and session handling
- [ ] Router prefixes (`app.include_router()`)
- [ ] Rate limiting middleware
- [ ] Full test suite
- [ ] Documentation website
- [ ] Python 3.14 free-threaded (no-GIL) optimization

---

## Contributing

Ignyx is early stage (v0.1.0) and contributions are very welcome. The Rust core engine is solid — the Python layer and platform support need the most work. See the roadmap above for where to start.

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT © [Saketh Jangala](https://github.com/sakethdevx)