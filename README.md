# � Ignyx

> **Ignite your API. Built in Rust, runs in Python.**

Ignyx is a high-performance, asynchronous web framework for Python, powered by a highly concurrent Rust core. 

## ⚡️ The Benchmark: ~8.7x Faster than FastAPI
Tested on MacBook Air M2 (native ARM64). Both frameworks configured identically (CORS + Pydantic + dynamic routing).

| Endpoint | Ignyx | FastAPI | Speedup | Latency |
| :--- | :--- | :--- | :--- | :--- |
| `/plaintext` | **53,886 req/s** | 6,193 req/s | **8.70x** | **2.22ms** |
| `/users/{id}` | **48,988 req/s** | 5,597 req/s | **8.75x** | **2.39ms** |
| `/users` (JSON) | **44,178 req/s** | 5,200 req/s | **8.49x** | **2.61ms** |

*(Tool: wrk -t4 -c100 -d10s)*

## 📦 Installation
```bash
pip install ignyx
```

## 🛠️ Quickstart
```python
from ignyx import Ignyx
app = Ignyx()

@app.get("/")
async def hello():
    return {"message": "Hello from Rust-powered Python!"}

app.run(host="0.0.0.0", port=8000)
```