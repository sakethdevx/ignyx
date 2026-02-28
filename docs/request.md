# Request Object

The `Request` object represents the incoming HTTP request and provides access to all its components like headers, query parameters, path parameters, and the request body.

## Overview

When a request hits your Ignyx application, a `Request` object is created. You can access it in your route handlers by type-hinting it in the function signature.

## Properties

The `Request` object has the following properties:

- `request.method`: The HTTP method (e.g., `"GET"`, `"POST"`).
- `request.path`: The request URL path (e.g., `"/users/me"`).
- `request.headers`: A case-insensitive dictionary of request headers.
- `request.query_params`: A dictionary containing query string parameters.
- `request.path_params`: A dictionary containing path parameters captured from the URL.
- `request.cookies`: A dictionary containing cookies sent with the request.
- `request.body`: The raw request body as bytes.
- `request.client_addr`: The IP address of the client (if available).

## Headers

Headers are accessed via a case-insensitive dictionary.

```python
@app.get("/debug")
def debug_headers(request: Request):
    user_agent = request.headers.get("User-Agent")
    api_key = request.headers.get("X-API-Key")
    return {"ua": user_agent, "key": api_key}
```

## Query Parameters

Query parameters are easily accessible and support basic type coercion.

```python
@app.get("/search")
def search(request: Request):
    q = request.query_params.get("q", "")
    page = int(request.query_params.get("page", 1))
    return {"query": q, "page": page}
```

## Body

Ignyx provides several ways to read the request body:

```python
@app.post("/submit")
async def submit(request: Request):
    # Read raw bytes
    raw_bytes = request.body
    
    # Read as text
    text = request.text()
    
    # Read as parsed JSON
    data = request.json()
    
    return {"received": data}
```

## Cookies

Cookies are parsed into a simple dictionary.

```python
@app.get("/check-session")
def check_session(request: Request):
    session_id = request.cookies.get("session_id")
    return {"session": session_id}
```

## Injecting Request

To use the `Request` object, simply add it to your handler parameters. Ignyx will automatically inject it.

```python
from ignyx import Request

@app.get("/")
def home(request: Request):
    return f"Hello, your path is {request.path}"
```
Note: You don't need to specify `Depends()` for the `Request` object; it is always available for injection by type alone.
