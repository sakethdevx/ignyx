# Response Classes

Ignyx provides a flexible way to return responses from your route handlers. Whether you want to return a simple dictionary, a custom response object, or a complex file download, Ignyx has you covered.

## Overview

Ignyx automatically handles several return types from your handlers:
- `dict` or `list`: Serialized to JSON.
- `str`: Returned as plain text or HTML.
- `tuple`: Allows returning body, status code, and headers together.
- `Response`: Built-in response classes for more control.

## Automated Response Detection

Ignyx is smart about what you return:

- **JSON**: If you return a `dict` or `list`, Ignyx sets `Content-Type: application/json`.
- **HTML**: If you return a `str` that starts with `<` (after stripping whitespace), Ignyx assumes it's HTML and sets `Content-Type: text/html`.
- **Text**: Otherwise, a `str` is returned as `application/json` (wrapped string) or you can use `PlainTextResponse`.

## JSONResponse

Use `JSONResponse` for explicit JSON responses with custom status codes.

```python
from ignyx.responses import JSONResponse

@app.get("/items/{id}")
def read_item(id: int):
    if id == 0:
        return JSONResponse({"error": "Invalid ID"}, status_code=400)
    return {"id": id, "name": "Item"}
```

## HTMLResponse

Return raw HTML content.

```python
from ignyx.responses import HTMLResponse

@app.get("/welcome")
def welcome():
    return HTMLResponse("<h1>Welcome to Ignyx!</h1>")
```

## PlainTextResponse

Return a plain text response.

```python
from ignyx.responses import PlainTextResponse

@app.get("/robots.txt")
def robots():
    return PlainTextResponse("User-agent: *\nDisallow: /")
```

## RedirectResponse

Perform HTTP redirects.

```python
from ignyx.responses import RedirectResponse

@app.get("/old-path")
def old_path():
    return RedirectResponse("/new-path", status_code=301)
```

## FileResponse

Serve files for download. Ignyx handles this efficiently from the Rust core.

```python
from ignyx.responses import FileResponse

@app.get("/download")
def download():
    return FileResponse("path/to/report.pdf", filename="UserReport.pdf")
```
*Note: Large files (>10MB) are currently buffered; streaming support is in development.*

## Tuple Syntax

For convenience, you can return a tuple to specify status and headers without importing response classes.

```python
@app.get("/simple")
def simple():
    # body, status_code
    return {"ok": True}, 201

@app.post("/custom")
def custom():
    # body, status_code, headers_dict
    return "Created", 201, {"X-Header": "Ignyx"}
```

## Cookies

You can set cookies using the `set_cookie` method on response objects.

```python
from ignyx.responses import JSONResponse

@app.post("/login")
def login():
    response = JSONResponse({"message": "Logged in"})
    response.set_cookie("session_id", "abc-123", max_age=3600, httponly=True)
    return response
```
Parameters for `set_cookie`:
- `key`: Cookie name.
- `value`: Cookie value.
- `max_age`: Lifetime in seconds.
- `path`: Cookie path (default: `/`).
- `domain`: Cookie domain.
- `secure`: HTTPS only (default: `False`).
- `httponly`: Prevents JS access (default: `False`).
- `samesite`: CSRF protection (`"Strict"`, `"Lax"`, or `"None"`).
