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
  <a href="https://github.com/sakethdevx/ignyx/actions">
    <img src="https://img.shields.io/badge/coverage-80%25-brightgreen" alt="Coverage">
  </a>
  <a href="https://pypi.org/project/ignyx/">
    <img src="https://img.shields.io/pypi/pyversions/ignyx" alt="Python versions">
  </a>
  <a href="https://sakethdevx.github.io/ignyx">
    <img src="https://img.shields.io/badge/docs-online-blue" alt="Docs">
  </a>
</p>

# Ignyx

> 📖 **[Full Documentation](https://sakethdevx.github.io/ignyx)**

Ignyx is a next-generation Python web framework engineered for maximum throughput, utilizing a Rust-powered HTTP core built on Hyper and Tokio. It provides a familiar, FastAPI-like decorator syntax, allowing developers to build high-performance APIs with zero learning curve. In honest benchmarks, Ignyx operates 8-9x faster than standard Python async frameworks.

## Features

- **Blazing Fast**: 8-9x faster than FastAPI in standard benchmarks.
- **Zero Overhead**: Owns the full HTTP pipeline — no ASGI overhead.
- **Hot Reload**: Blazing fast development with built-in file watcher.
- **Pydantic v2**: Deep integration for request body validation.
- **Advanced OpenAPI**: Auto-generates schemas with Pydantic model support.
- **Dependency Injection**: Familiar `Depends()` pattern for clean logic.
- **WebSockets**: Native, high-concurrency WebSocket support.
- **Modular**: Organize APIs with `Router` prefixes.
- **Typed**: Shipped with `py.typed` for perfect IDE autocompletion.

## Benchmark

*Apple M2, `wrk -t4 -c100 -d10s`*

| Endpoint           | Ignyx        | FastAPI     | Speedup |
| ------------------ | ------------ | ----------- | ------- |
| `/plaintext`       | 51,771 req/s | 5,846 req/s | 🔥 8.8x |
| `/json`            | 37,138 req/s | 4,844 req/s | 🔥 7.6x |
| `/users/{id}`      | 43,261 req/s | 5,306 req/s | 🔥 8.1x |

*Note: Ignyx tested with native Rust core. FastAPI tested with Uvicorn single worker — standard config.*

## Installation

```bash
pip install ignyx==2.1.3
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
    app.run(host="0.0.0.0", port=8000, reload=True)
```

## Feature Examples

<details>
<summary><b>Pydantic Validation</b></summary>

```python
from ignyx import Ignyx
from pydantic import BaseModel

app = Ignyx()

class User(BaseModel):
    name: str
    age: int

@app.post("/users")
async def create_user(user: User):
    return {"status": "success", "data": user.model_dump()}
```
</details>

<details>
<summary><b>Path + Query Parameters</b></summary>

```python
from ignyx import Ignyx

app = Ignyx()

@app.get("/users/{id}")
async def get_user(id: int, format: str = "json"):
    return {"id": id, "format": format}
```
</details>

<details>
<summary><b>Dependency Injection</b></summary>

```python
from ignyx import Ignyx, Depends

app = Ignyx()

def get_db():
    db = Database()
    try:
        yield db
    finally:
        db.close()

@app.get("/users")
async def get_users(db = Depends(get_db)):
    return db.query("SELECT * FROM users")
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
        await ws.send_text(f"Echo: {data}")
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
| Hot Reload             | ✅ | ✅     |
| Native Rust Core       | ✅ | ❌     |

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=sakethdevx/ignyx&type=Date)](https://star-history.com/#sakethdevx/ignyx&Date)

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on how to set up your development environment.

## Deployment Note

Ignyx manages its own Tokio runtime. No Uvicorn or Gunicorn needed. Just `python app.py`.

## License

This project is licensed under the [MIT License](LICENSE).