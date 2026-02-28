# Middleware

Middleware is a powerful way to intercept and process requests and responses globally in your Ignyx application. It allows you to add cross-cutting concerns like logging, authentication, CORS, and rate limiting.

## Overview

The middleware lifecycle in Ignyx follows three main stages:
1. **`before_request`**: Executed before the request reaches the route handler.
2. **`after_request`**: Executed after the route handler has processed the request.
3. **`on_error`**: Executed if an exception occurs during request processing.

## Basic Example: Custom Logging Middleware

You can create custom middleware by extending the `Middleware` base class.

```python
from ignyx.middleware import Middleware
import time

class LoggingMiddleware(Middleware):
    def before_request(self, request):
        request.state.start_time = time.time()

    def after_request(self, request, response):
        process_time = time.time() - request.state.start_time
        print(f"{request.method} {request.path} completed in {process_time:.4f}s")
        response.headers["X-Process-Time"] = str(process_time)
        return response

app.add_middleware(LoggingMiddleware)
```

## CORSMiddleware

Ignyx provides a built-in `CORSMiddleware` to handle Cross-Origin Resource Sharing.

```python
from ignyx.middleware import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=True,
    max_age=3600
)
```

### Parameters:
- `allow_origins`: List of allowed origins. Use `["*"]` for all.
- `allow_methods`: List of allowed HTTP methods.
- `allow_headers`: List of allowed request headers.
- `allow_credentials`: Whether to allow cookies in cross-origin requests.
- `max_age`: Time in seconds to cache preflight responses.

## RateLimitMiddleware

Protect your API from abuse with the `RateLimitMiddleware`.

```python
from ignyx.middleware import RateLimitMiddleware

app.add_middleware(
    RateLimitMiddleware,
    requests_per_window=100,
    window_seconds=60
)
```
This example limits clients to 100 requests per minute.

## AccessLogMiddleware

Standardize your application logs with `AccessLogMiddleware`.

```python
from ignyx.middleware import AccessLogMiddleware

app.add_middleware(AccessLogMiddleware, logger_name="ignyx.access")
```
It logs request method, path, status code, and latency in a clean format.

## Writing Custom Middleware

To write your own middleware, inherit from `ignyx.middleware.Middleware` and override the lifecycle methods you need.

```python
from ignyx.middleware import Middleware

class MyMiddleware(Middleware):
    def __init__(self, some_config=None):
        self.some_config = some_config

    def before_request(self, request):
        # Do something before handler
        pass

    def after_request(self, request, response):
        # Do something after handler
        return response

    def on_error(self, request, error):
        # Handle error
        pass
```

## Middleware Ordering

The order in which you call `app.add_middleware()` matters. Middleware added first will execute its `before_request` first, but its `after_request` will execute last (wrapping the inner layers).

```python
app.add_middleware(MiddlewareA)
app.add_middleware(MiddlewareB)

# Execution Flow:
# MiddlewareA.before -> MiddlewareB.before -> Handler -> MiddlewareB.after -> MiddlewareA.after
```
