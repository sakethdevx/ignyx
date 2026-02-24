"""
Full-featured Ignyx demo app exercising all Phase 2 features:
- Multiple routes with different methods
- Middleware (CORS)
- OpenAPI / Swagger UI / ReDoc
- Dependency injection
- Background tasks
- Error handling (dev mode)
"""
from ignyx import Ignyx, Depends
from ignyx.middleware import CORSMiddleware

app = Ignyx(
    title="Ignyx Demo API",
    version="0.1.0",
    debug=True,
    description="A demo API showcasing Ignyx features",
)

# Add CORS middleware
app.add_middleware(CORSMiddleware(
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
))


# --- Dependency injection ---
def get_db():
    """Simulate a database connection."""
    return {"connection": "active", "type": "sqlite"}


# --- Routes ---

@app.get("/")
def hello():
    """Hello world endpoint."""
    return {"message": "Ignyx is live", "version": "0.1.0"}


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/users/{user_id}")
def get_user():
    """Fetch a user by ID."""
    return {"user_id": "123", "name": "John Doe", "email": "john@example.com"}


@app.post("/users")
def create_user():
    """Create a new user."""
    return {"status": "created", "user_id": "456"}


@app.get("/items")
def list_items():
    """List all items."""
    return {
        "items": [
            {"id": 1, "name": "Item 1", "price": 9.99},
            {"id": 2, "name": "Item 2", "price": 19.99},
            {"id": 3, "name": "Item 3", "price": 29.99},
        ]
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
