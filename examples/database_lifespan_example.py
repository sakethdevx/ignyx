"""
Database Lifespan & Connection Pool Management with Ignyx.

Demonstrates the official pattern for managing async database connection pools
using SQLAlchemy 2.0 with Ignyx's @app.on_startup / @app.on_shutdown lifecycle hooks.

The pattern:
  1. Create the engine/pool once at startup — stored on app.state
  2. Inject the session via Depends() into any route that needs it
  3. Tear down the pool cleanly at shutdown

Requirements (for real use):
    pip install sqlalchemy[asyncio] asyncpg  # or aiosqlite for SQLite

This example uses aiosqlite with the in-memory SQLite backend so it runs
with zero external dependencies for demonstration purposes.
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

# ---------------------------------------------------------------------------
# Optional real SQLAlchemy imports — gracefully mocked if not installed
# ---------------------------------------------------------------------------
try:
    from sqlalchemy import Integer, String, select
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
    _SQLALCHEMY_AVAILABLE = True
except ImportError:
    _SQLALCHEMY_AVAILABLE = False  # type: ignore[assignment]

try:
    from pydantic import BaseModel, Field
except ImportError:
    BaseModel = object  # type: ignore[assignment, misc]

    def Field(*a, **kw):  # type: ignore[no-redef]
        return None

from ignyx import Depends, Ignyx
from ignyx.responses import JSONResponse

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = Ignyx(
    title="Ignyx DB Lifespan Demo",
    version="2.5.0",
    description="Connection pool management with SQLAlchemy 2.0 async",
)

# ---------------------------------------------------------------------------
# SQLAlchemy model (only if available)
# ---------------------------------------------------------------------------
if _SQLALCHEMY_AVAILABLE:
    class Base(DeclarativeBase):
        pass

    class User(Base):  # type: ignore[valid-type]
        __tablename__ = "users"
        id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
        name: Mapped[str] = mapped_column(String(100), nullable=False)
        email: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):  # type: ignore[misc]
    """Schema for creating a new user."""
    name: str = Field(..., min_length=1, max_length=100, description="Full name")
    email: str = Field(..., description="Email address")


class UserOut(BaseModel):  # type: ignore[misc]
    """Schema returned by user endpoints."""
    id: int
    name: str
    email: str


# ---------------------------------------------------------------------------
# Lifecycle: startup creates the pool, shutdown disposes it
# ---------------------------------------------------------------------------
@app.on_startup
async def create_db_pool() -> None:
    """
    Create the async database engine and connection pool.

    The engine (and therefore its pool) is stored on app.state so every
    request handler can reach it through the Depends() injection pattern.

    For PostgreSQL swap the URL:
        "postgresql+asyncpg://user:pass@localhost/dbname"
    """
    print("🗄️  Opening database connection pool…")

    if not _SQLALCHEMY_AVAILABLE:
        print("   ⚠️  SQLAlchemy not installed — using mock state")
        app.state.db_engine = None
        app.state.db_session_factory = None
        app.state.mock_users: list[dict[str, Any]] = []
        return

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        pool_size=5,          # keep 5 connections warm
        max_overflow=10,      # allow 10 extra connections under load
        pool_timeout=30,      # wait up to 30s for a free connection
        pool_recycle=1800,    # recycle connections every 30 min
        echo=False,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # session_factory is reusable across all requests
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    app.state.db_engine = engine
    app.state.db_session_factory = session_factory
    print("   ✅ Connection pool ready (pool_size=5, max_overflow=10)")


@app.on_shutdown
async def close_db_pool() -> None:
    """
    Dispose the engine and drain the connection pool gracefully.
    Always called even if a request is in flight — Ignyx waits for
    the current request to finish before triggering shutdown.
    """
    print("🗄️  Closing database connection pool…")

    if not _SQLALCHEMY_AVAILABLE or app.state.db_engine is None:
        return

    await app.state.db_engine.dispose()
    print("   ✅ Pool drained cleanly")


# ---------------------------------------------------------------------------
# Dependency: yield a session per-request
# ---------------------------------------------------------------------------
@asynccontextmanager
async def _session_ctx() -> AsyncGenerator[Any, None]:
    """Internal async context manager for a single-request session."""
    factory = app.state.db_session_factory
    if factory is None:
        yield None
        return
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db_session() -> AsyncGenerator[Any, None]:
    """
    Dependency that yields a scoped AsyncSession for the current request.

    Usage in a route:
        @app.get("/users")
        async def list_users(db=Depends(get_db_session)):
            ...
    """
    async with _session_ctx() as session:
        yield session


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/users", tags=["users"])
async def list_users(db: Any = Depends(get_db_session)) -> Any:
    """List all users from the database."""
    if not _SQLALCHEMY_AVAILABLE or db is None:
        return {"users": app.state.mock_users}

    result = await db.execute(select(User))
    users = result.scalars().all()
    return {"users": [{"id": u.id, "name": u.name, "email": u.email} for u in users]}


@app.post("/users", tags=["users"])
async def create_user(body: UserCreate, db: Any = Depends(get_db_session)) -> Any:  # type: ignore[valid-type]
    """Create a new user and persist to the database."""
    if not _SQLALCHEMY_AVAILABLE or db is None:
        # mock path
        new_id = len(app.state.mock_users) + 1
        record: dict[str, Any] = {"id": new_id, "name": body.name, "email": body.email}
        app.state.mock_users.append(record)
        return JSONResponse(record, status_code=201)

    user = User(name=body.name, email=body.email)
    db.add(user)
    await db.flush()
    return JSONResponse(
        {"id": user.id, "name": user.name, "email": user.email},
        status_code=201,
    )


@app.get("/users/{user_id}", tags=["users"])
async def get_user(user_id: int, db: Any = Depends(get_db_session)) -> Any:
    """Fetch a single user by ID."""
    if not _SQLALCHEMY_AVAILABLE or db is None:
        for u in app.state.mock_users:
            if u["id"] == user_id:
                return u
        return JSONResponse({"error": "User not found"}, status_code=404)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return JSONResponse({"error": "User not found"}, status_code=404)
    return {"id": user.id, "name": user.name, "email": user.email}


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Database connectivity health-check."""
    engine = getattr(app.state, "db_engine", None)
    if engine is None and _SQLALCHEMY_AVAILABLE:
        return {"status": "degraded", "database": "pool not initialised"}
    pool_info = {}
    if engine is not None:
        pool = engine.pool
        pool_info = {
            "pool_size": str(pool.size()),
            "checked_out": str(pool.checkedout()),
        }
    return {"status": "healthy", "database": "connected", **pool_info}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
