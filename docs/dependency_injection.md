# Dependency Injection

Dependency Injection (DI) is a powerful pattern in Ignyx that allows you to declare dependencies for your route handlers. Ignyx then takes care of resolving these dependencies, providing you with the necessary objects automatically.

## Overview

The `Depends()` pattern allows you to write reusable logic that can be shared across multiple routes. This is useful for:
- Authentication and authorization
- Database connection management
- Shared configuration
- Request pre-processing

When you use `Depends()`, Ignyx calls the dependency for you and passes the result to your handler.

## Basic Example

Here's a simple example of using `Depends()` to extract a token from a header.

```python
from ignyx import Ignyx, Depends, Request

app = Ignyx()

def get_current_user(request: Request):
    token = request.headers.get("Authorization")
    if not token:
        # In a real app, you would raise an HTTPException here
        return "Anonymous"
    return {"id": 1, "name": "Saketh"}

@app.get("/users/me")
def read_current_user(user = Depends(get_current_user)):
    return user
```

## Advanced Example: Chained Dependencies

Dependencies can also depend on other dependencies, allowing you to create complex authentication or data retrieval chains.

```python
from ignyx import Ignyx, Depends, Request

app = Ignyx()

def get_db():
    return {"session": "active_db_session"}

def get_current_user(db = Depends(get_db)):
    # Use db session to find user
    return {"id": 1, "username": "sakethdevx"}

def get_active_user(user = Depends(get_current_user)):
    if user.get("disabled"):
        raise HTTPException(400, "User inactive")
    return user

@app.get("/items")
def read_items(user = Depends(get_active_user)):
    return {"user": user, "items": ["item1", "item2"]}
```

## Generator Dependencies

Ignyx supports generator dependencies using `yield`. This is perfect for resources that need cleanup, such as database sessions or file handles.

```python
def get_db():
    db = DatabaseSession()
    try:
        yield db
    finally:
        db.close() # cleanup happens after route execution
```

## Testing

You can easily override dependencies in your tests using the `dependency_overrides` attribute of the `Ignyx` app or `TestClient`.

```python
from ignyx.testclient import TestClient

def override_get_current_user():
    return {"id": 999, "name": "Test User"}

app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)
response = client.get("/users/me")
assert response.json()["id"] == 999
```

## API Reference

### `Depends(dependency, use_cache=True)`

- `dependency`: A callable (function, class).
- `use_cache`: If `True`, the result of the dependency is cached for the duration of a single request. If multiple routes or dependencies depend on the same callable, it will only be executed once per request.
