# Static Files

Ignyx provides a high-performance way to serve static assets like images, CSS, and JavaScript files using the `StaticFiles` class.

## Overview

Serving static files in Ignyx is handled by mounting a `StaticFiles` instance to a specific path prefix. The file serving logic is implemented in Rust, ensuring minimal overhead and zero-copy transfers when possible.

## Basic Usage

Mount a directory to a path like `/static`.

```python
from ignyx import Ignyx
from ignyx.staticfiles import StaticFiles

app = Ignyx()

# Files in the "static" directory will be available at /static/*
app.mount("/static", StaticFiles(directory="static"))
```

If you have a file `static/logo.png`, it will be accessible at `http://localhost:8000/static/logo.png`.

## Serving a Single Page Application (SPA)

If you are serving a modern frontend framework like React or Vue, you can enable `html=True` to serve an `index.html` file when a directory is requested.

```python
app.mount("/", StaticFiles(directory="dist", html=True))
```
This is useful for professional production deployments where the backend serves the frontend assets directly.

## MIME Type Auto-Detection

Ignyx automatically detects the correct `Content-Type` header for common file extensions based on your operating system's MIME database.

- `.html` -> `text/html`
- `.css` -> `text/css`
- `.js` -> `application/javascript`
- `.png` -> `image/png`
- `.json` -> `application/json`

## Security

Ignyx includes built-in protection against path traversal attacks. It ensures that requests cannot access files outside of the specified `directory` by normalizing paths and checking boundaries before reading any data.

## API Reference

### `StaticFiles(directory, html=False)`

- `directory`: The local directory to serve files from.
- `html`: If `True`, automatically looks for `index.html` in directories and supports sub-path routing for SPAs.
