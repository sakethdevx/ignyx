# Quickstart

Install Ignyx via pip:

```bash
pip install ignyx
```

Create a basic app:

```python
from ignyx import Ignyx

app = Ignyx()

@app.get("/")
async def root():
    return {"message": "Ignited!"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```

Once the server is running, open:

- `http://localhost:8000/scalar` for the modern Scalar API reference
- `http://localhost:8000/docs` for Swagger UI
- `http://localhost:8000/redoc` for ReDoc
- `http://localhost:8000/openapi.json` for the raw OpenAPI schema

If you want to paginate list endpoints, see [Pagination](pagination.md).
