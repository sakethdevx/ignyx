# Routing

Routing in Ignyx is handled by a high-performance Radix Tree router implemented in Rust using the `matchit` crate. It supports path parameters, query parameters, and modular routing via `Router` prefixes.

## Overview

Routes are defined using decorators on your `Ignyx` app instance or a `Router` instance. Ignyx uses the function signature to determine which parameters to inject (path params, query params, request object, etc.).

## Path Parameters with Types

You can capture values from the URL using curly braces. Ignyx supports type coercion for common types.

```python
@app.get("/users/{user_id}")
def get_user(user_id: int):
    # user_id is automatically converted to an int
    return {"id": user_id}

@app.get("/files/{file_path}")
def get_file(file_path: str):
    return {"path": file_path}
```

## Query Parameters

Any function parameter that is not a path parameter and not a complex type (like `Request` or a Pydantic model) is treated as a query parameter.

```python
@app.get("/items")
def search_items(q: str, limit: int = 10, offset: int = 0):
    return {
        "query": q,
        "limit": limit,
        "offset": offset
    }
```

## Router: Prefix + Include

For larger applications, you can organize your routes into multiple files using the `Router` class.

**users_router.py:**
```python
from ignyx import Router

router = Router()

@router.get("/")
def list_users():
    return [{"id": 1}]

@router.get("/{id}")
def get_user(id: int):
    return {"id": id}
```

**app.py:**
```python
from ignyx import Ignyx
from .users_router import router as users_router

app = Ignyx()
app.include_router(users_router, prefix="/users")
```

## HTTP Methods

Ignyx supports all standard HTTP methods:

```python
@app.get("/")
def read(): ...

@app.post("/")
def create(): ...

@app.put("/")
def update(): ...

@app.delete("/")
def delete(): ...

@app.patch("/")
def patch(): ...
```

## 404 Handling

You can customize the 404 Not Found response using the `exception_handler` decorator.

```python
from ignyx import Ignyx, JSONResponse

app = Ignyx()

@app.exception_handler(404)
def custom_404(request, exc):
    return JSONResponse(
        {"error": "Custom Not Found", "path": request.path},
        status_code=404
    )
```

## API Reference

### `app.get(path)`, `app.post(path)`, etc.
Decorators for registering routes.

### `app.include_router(router, prefix="")`
Integrates a `Router` instance into the application.

### `Router()`
Class for creating modular groups of routes.
