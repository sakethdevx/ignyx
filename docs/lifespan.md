# Lifespan Events

Lifespan events allow you to run logic at the beginning and end of your Ignyx application's lifecycle. This is perfect for managing resources that should exist for the entire duration of the server.

## Overview

Ignyx provides two main decorators for lifespan management:
- `@app.on_startup`: Executed once when the server starts listening for requests.
- `@app.on_shutdown`: Executed once when the server receives a shutdown signal.

## Database Connections

Use startup events to initialize database connection pools once, instead of per-request.

```python
from ignyx import Ignyx

app = Ignyx()
db_pool = None

@app.on_startup
async def setup_db():
    global db_pool
    db_pool = await create_db_pool("postgres://...")
    print("Database connection established")

@app.on_shutdown
async def close_db():
    await db_pool.close()
    print("Database connection closed")
```

## Application State

You can use `app.state` to store objects that need to be accessed by your dependencies and route handlers. `app.state` is a thread-safe `SimpleNamespace`.

```python
@app.on_startup
def init_cache():
    app.state.cache = RedisCache()

@app.get("/items")
def get_items():
    # Access state in handlers
    return app.state.cache.get("items")
```

## Async Startup Handlers

Ignyx supports both `def` and `async def` for lifespan handlers. If you use `async def`, Ignyx will run the task within the global event loop before the server starts accepting traffic.

```python
@app.on_startup
async def warm_cache():
    await perform_heavy_async_warmup()
```

## API Reference

### `@app.on_startup`
Decorator for functions to run on startup.

### `@app.on_shutdown`
Decorator for functions to run on shutdown.

### `app.state`
A storage object for application-wide data.
