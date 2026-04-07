# Pagination

Ignyx includes built-in limit/offset pagination in `ignyx.pagination`.

## Imports

```python
from ignyx.pagination import Page, paginate
```

## What `paginate()` Does

`paginate()` reads `limit` and `offset` from the incoming request, slices the provided dataset or query-like object, and returns a standardized `Page[T]` response.

The response shape includes:

- `total_items`
- `next_page`
- `items`

## Basic Example

```python
from ignyx import Ignyx
from ignyx.pagination import Page, paginate
from ignyx.request import Request
from pydantic import BaseModel

app = Ignyx()

class ProductOut(BaseModel):
    id: int
    name: str

PRODUCTS = [
    ProductOut(id=1, name="Keyboard"),
    ProductOut(id=2, name="Mouse"),
    ProductOut(id=3, name="Monitor"),
]

@app.get("/products")
def list_products(request: Request) -> Page[ProductOut]:
    return paginate(request, PRODUCTS, default_limit=2)
```

Request:

```http
GET /products?limit=2&offset=0
```

Response:

```json
{
  "total_items": 3,
  "next_page": "/products?limit=2&offset=2",
  "items": [
    {"id": 1, "name": "Keyboard"},
    {"id": 2, "name": "Mouse"}
  ]
}
```

## Query Parameters

- `limit`: Maximum number of items to return.
- `offset`: Number of items to skip before slicing.

If a value is missing or invalid, Ignyx falls back to the defaults you pass into `paginate()`.

## Configuring Limits

```python
@app.get("/orders")
def list_orders(request: Request):
    return paginate(
        request,
        orders_query,
        default_limit=25,
        max_limit=100,
    )
```

## ORM And Query Support

`paginate()` works with:

- Python sequences like `list` and `tuple`
- iterables
- query-like objects that expose methods such as `count()`, `offset()`, `limit()`, and `all()`

This makes it usable for both in-memory data and common ORM query patterns.

## Response Model

`Page[T]` is a generic Pydantic model, so your return annotations stay expressive and your generated OpenAPI schema stays consistent.

```python
@app.get("/users")
def list_users(request: Request) -> Page[UserOut]:
    return paginate(request, users_query)
```
