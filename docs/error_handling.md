# Error Handling

Handling errors gracefully is essential for a professional API. Ignyx provides built-in mechanisms for raising HTTP exceptions and registering custom error handlers for both HTTP statuses and generic Python exceptions.

## Overview

You can handle errors at two levels:
1. **Implicitly**: By raising an `HTTPException`.
2. **Explicitly**: By defining custom handlers with the `@app.exception_handler` decorator.

## Raising HTTPException

The `HTTPException` class allows you to return an error response from anywhere in your code (including deep inside dependencies).

```python
from ignyx import Ignyx, HTTPException

app = Ignyx()

@app.get("/items/{id}")
def read_item(id: int):
    if id not in database:
        raise HTTPException(
            status_code=404,
            detail=f"Item {id} not found",
            headers={"X-Error": "Not Found"}
        )
    return database[id]
```

## Custom Status Handlers

You can override the default behavior for specific HTTP status codes.

```python
from ignyx import Ignyx, JSONResponse

@app.exception_handler(404)
def not_found_handler(request, exc):
    return JSONResponse(
        {"error": "Resource Missing", "path": request.path},
        status_code=404
    )
```

## Exception Type Handlers

You can also register handlers for specific Python exception types. This is useful for catching errors from external libraries (like SQLAlchemy or Pydantic) and converting them into uniform API responses.

```python
@app.exception_handler(ValueError)
def value_error_handler(request, exc):
    return JSONResponse(
        {"error": "Value Error", "message": str(exc)},
        status_code=400
    )
```

## Global Error Response Format

By default, Ignyx returns error responses in a standard JSON format:

```json
{
    "detail": "Actual error message"
}
```
Validation errors use a more detailed structure inspired by Pydantic's error format.

## API Reference

### `HTTPException(status_code, detail=None, headers=None)`
Exception class for returning HTTP errors.

### `@app.exception_handler(status_code_or_type)`
Decorator for registering custom error handling functions.
