# API Docs

Ignyx generates an OpenAPI schema automatically and serves multiple API documentation UIs out of the box.

## Default Endpoints

- `GET /scalar`: Modern Scalar API reference.
- `GET /docs`: Swagger UI.
- `GET /redoc`: ReDoc.
- `GET /openapi.json`: Raw OpenAPI schema.

## Why Scalar Is The Default DX Upgrade

Phase 15 introduces Scalar as the polished, modern documentation surface for API consumers. It gives Ignyx apps a more professional API reference experience immediately, while still keeping Swagger UI and ReDoc available for compatibility and team preference.

## Example

```python
from ignyx import Ignyx

app = Ignyx(
    title="Payments API",
    description="Production-ready payment endpoints",
)
```

With the default configuration:

- `http://localhost:8000/scalar`
- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`
- `http://localhost:8000/openapi.json`

## Customizing Paths

You can customize all documentation endpoints when creating the app.

```python
from ignyx import Ignyx

app = Ignyx(
    scalar_url="/reference",
    docs_url="/swagger",
    redoc_url="/redoc-ui",
    openapi_url="/schema.json",
)
```

That configuration serves:

- `/reference`
- `/swagger`
- `/redoc-ui`
- `/schema.json`

## OpenAPI Integration

Ignyx extracts:

- path and query parameters from handler signatures
- request bodies from Pydantic models
- response models from return annotations
- operation summaries and descriptions from docstrings

That means your docs stay in sync with your handlers without extra schema registration.
