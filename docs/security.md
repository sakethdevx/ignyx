# Security

Ignyx includes several utilities to help you secure your API endpoints with common authentication schemes like OAuth2, API Keys, and HTTP Basic authentication.

## Overview

Security utilities in Ignyx are designed to be used with the `Depends()` pattern. They extract credentials from the request (headers, cookies, or query params) and can be used to authenticate users before the route handler is executed.

## OAuth2PasswordBearer

This utility extracts a Bearer token from the `Authorization` header.

```python
from ignyx import Ignyx, Depends
from ignyx.security import OAuth2PasswordBearer

app = Ignyx()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.get("/items")
def read_items(token: str = Depends(oauth2_scheme)):
    return {"token": token}
```

## APIKeyHeader

Extract an API key from a custom header.

```python
from ignyx.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

@app.get("/secure-data")
def get_secure_data(api_key: str = Depends(api_key_header)):
    if api_key != "secret-key":
        raise HTTPException(403, "Invalid API Key")
    return {"data": "highly-sensitive"}
```

## HTTPBasic

Standard HTTP Basic authentication (Username/Password).

```python
from ignyx.security import HTTPBasic

security = HTTPBasic()

@app.get("/admin")
def admin_panel(credentials = Depends(security)):
    # credentials has .username and .password
    return {"admin": credentials.username}
```

## Using with Depends()

You typically wrap these security schemes in a higher-level dependency to fetch user data from a database.

```python
def get_current_user(token: str = Depends(oauth2_scheme)):
    user = db.fetch_user_by_token(token)
    if not user:
        raise HTTPException(401, "Invalid credentials")
    return user

@app.get("/me")
def me(user = Depends(get_current_user)):
    return user
```

## Production HTTPS Note

In production, you should **always** run your Ignyx application behind a TLS/SSL proxy (like Nginx, Caddy, or a Cloud Load Balancer) to ensure that credentials sent via headers are encrypted.

## API Reference

### `OAuth2PasswordBearer(tokenUrl)`
Extracts Bearer token from `Authorization` header.

### `APIKeyHeader(name)`
Extracts value from the specified header.

### `HTTPBasic()`
Extracts and decodes Basic credentials.
