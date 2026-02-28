# Security

Ignyx provides built-in utilities for handling common authentication and authorization patterns. These utilities integrate directly with the Dependency Injection system to provide a clean, typed interface for securing your endpoints.

## Overview

Security in Ignyx is handled via **Security Schemes**. These objects are used as dependencies with `Depends()`. When a security scheme is used:
1. It automatically extracts credentials (tokens, keys, or credentials) from the request.
2. It documents the security requirements in the auto-generated OpenAPI (Swagger) schema.
3. It provides the extracted data directly to your route handler or high-level dependency.

## Basic Example

Using `OAuth2PasswordBearer` to protect a route with a Bearer token.

```python
from ignyx import Ignyx, Depends
from ignyx.security import OAuth2PasswordBearer

app = Ignyx()
# tokenUrl is where the client should send username/password to get a token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

@app.get("/users/me")
async def read_current_user(token: str = Depends(oauth2_scheme)):
    return {"token": token}
```

## Advanced Example

Combining a security scheme with a high-level dependency to fetch a real User object from a database.

```python
from typing import Optional
from ignyx import Ignyx, Depends, HTTPException
from ignyx.security import APIKeyHeader
from pydantic import BaseModel

app = Ignyx()
api_key_scheme = APIKeyHeader(name="X-API-Key")

class User(BaseModel):
    username: str
    is_admin: bool

async def get_current_user(api_key: str = Depends(api_key_scheme)) -> User:
    # In a real app, you would look this up in a database
    if api_key == "top-secret-key":
        return User(username="admin", is_admin=True)
    
    raise HTTPException(status_code=401, detail="Invalid API Key")

@app.get("/admin/dashboard")
async def admin_dashboard(user: User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return {"message": f"Welcome, {user.username}!"}
```

## API Reference

### `OAuth2PasswordBearer`
- **Purpose**: Extracts a Bearer token from the `Authorization` header.
- **Parameters**:
    - `tokenUrl` (str): The URL that provides the token (used in Swagger UI).
    - `auto_error` (bool): If `True`, automatically raises 401 if token is missing. Default `True`.

### `APIKeyHeader`
- **Purpose**: Extracts an API key from a specific request header.
- **Parameters**:
    - `name` (str): The name of the header to check.
    - `auto_error` (bool): If `True`, automatically raises 401 if header is missing. Default `True`.

### `HTTPBasic`
- **Purpose**: Extracts and decodes Username/Password from the `Authorization: Basic` header.
- **Returns**: An object with `.username` and `.password` attributes.

## Common Patterns

### Chained Security
You can create dependencies that require other dependencies, allowing you to build complex authorization logic. For example, `get_current_active_user` might depend on `get_current_user`.

### Optional Security
By setting `auto_error=False` on the security scheme, you can make authentication optional. The dependency will return `None` if the credentials are missing instead of raising an exception.

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

@app.get("/")
async def root(token: Optional[str] = Depends(oauth2_scheme)):
    if token:
        return {"message": "Logged in"}
    return {"message": "Guest"}
```

## Notes & Gotchas

- **Production Security**: Security utilities only extract and decode credentials. They do **not** verify tokens (like JWT signatures). That logic should be implemented in your dependency functions.
- **HTTPS**: Always run Ignyx behind a TLS/SSL proxy (like Nginx) in production. Security schemes pass sensitive data in headers which must be encrypted.
- **OpenAPI**: Using these built-in utilities ensures that the "Authorize" button in Swagger UI works correctly for your API.
