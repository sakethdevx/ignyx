# Ignyx Benchmark Report — Honest Numbers

> **Machine**: Apple Silicon M2, native ARM64
> **Python**: 3.12
> **Rust**: 1.93.1, release profile (LTO=fat, opt-level=3)
> **Tool**: `wrk -t4 -c100 -d10s`
> **Methodology**: Every request acquires the GIL and calls the Python handler. No response caching. No shortcuts.

## Results

| Endpoint | Ignyx (req/s) | FastAPI (req/s) | Speedup |
|----------|-------------:|----------------:|--------:|
| `/plaintext` | **51,771** | 5,846 | **8.8x** |
| `/json` | **37,138** | 4,844 | **7.6x** |
| `/users/42` (path param) | **43,261** | 5,306 | **8.1x** |

## Latency

| Endpoint | Ignyx (avg) | FastAPI (avg) |
|----------|------------:|--------------:|
| `/plaintext` | 2.46ms | 17.32ms |
| `/json` | 4.21ms | 21.23ms |
| `/users/42` | 3.42ms | 18.89ms |

## What's happening on each request

**Ignyx:**
1. Tokio event loop receives connection
2. Hyper parses HTTP
3. matchit routes the path (radix tree lookup)
4. Path parameters extracted (e.g., `{id}` → `"42"`)
5. GIL acquired via `Python::with_gil()`
6. `HandlerSignature` cache consulted for type annotations
7. Path string coerced (`"42"` → `int(42)`) in PyO3
8. Python handler called with kwargs
9. Return value serialized (dict → `json.dumps()`, str → plaintext)
10. GIL released
11. Hyper sends response

**FastAPI:**
1. Uvicorn receives connection (asyncio + httptools/h11)
2. Starlette routes the path
3. FastAPI dependency injection, validation, serialization via Pydantic
4. Handler called
5. Response serialized and sent

## Why Ignyx is faster

- **Hyper vs Uvicorn**: Hyper (Rust) is fundamentally faster than Uvicorn (Python + C extension)
- **matchit vs Starlette router**: Radix tree vs linear route matching
- **Signature Caching**: Ignyx caches handler arguments via `inspect` on start-up. No reflection during requests.
- **Minimal overhead**: Ignyx does raw `json.dumps()`. FastAPI runs Pydantic serialization on every response.
- **No ASGI overhead**: Ignyx bypasses the ASGI protocol entirely — direct Rust HTTP → Python handler → Rust response.

## Honest caveats

- FastAPI's numbers include Pydantic validation overhead which provides value (type safety, serialization). Ignyx currently relies on PyO3 coercion but delegates deeper validation to the user.
- All tests on Rosetta 2 (x86_64 emulation on Apple Silicon). Native ARM builds would likely be faster for both.
