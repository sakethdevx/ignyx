# 🔥 Ignyx

**Ignite your API. Built in Rust, runs in Python.**

Ignyx is a high-performance Python web framework powered by Rust (Hyper + Tokio + PyO3). It delivers **50K+ req/sec** — 8x faster than FastAPI.

## Benchmarks

| Framework | JSON req/s | Plaintext req/s |
|-----------|----------:|----------------:|
| 🔥 **Ignyx** | **37,138** | **51,771** |
| FastAPI | 4,844 | 5,846 |

## Quick Start

```python
from ignyx import Ignyx

app = Ignyx()

@app.get("/")
def hello():
    return {"message": "Hello, World!"}

@app.get("/users/{user_id}")
def get_user():
    return {"user_id": "123", "name": "John Doe"}

app.run(host="0.0.0.0", port=8000)
```

## Features

- ⚡ **50K+ req/sec** — Rust HTTP core (Hyper + Tokio)
- 🎯 **FastAPI-like syntax** — Familiar decorator-based routing
- 📖 **Auto-generated docs** — Swagger UI at `/docs`, ReDoc at `/redoc`
- 🔧 **Middleware** — Before/after/error middleware with CORS built-in
- 💉 **Dependency Injection** — FastAPI-style `Depends()`
- 📋 **OpenAPI 3.0** — Auto-generated from your routes
- 🎯 **Radix tree routing** — O(1) route matching via `matchit`
- 🛡️ **Error handling** — Dev mode (full traces) & prod mode (clean JSON)
- 🔄 **Background tasks** — Run tasks after response

## Installation

```bash
pip install ignyx
```

## Middleware

```python
from ignyx import Ignyx
from ignyx.middleware import CORSMiddleware

app = Ignyx(debug=True)

app.add_middleware(CORSMiddleware(
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
))
```

## Dependency Injection

```python
from ignyx import Ignyx, Depends

def get_db():
    return {"connection": "active"}

@app.get("/users")
def get_users(db=Depends(get_db)):
    return {"db": db}
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Rust + Python |
| Python Bindings | PyO3 + maturin |
| Async Runtime | Tokio |
| HTTP Layer | Hyper |
| Router | matchit (radix tree) |
| Serialization | serde + serde_json |

## License

MIT
