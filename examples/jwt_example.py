"""
JWT authentication example for Ignyx.

Demonstrates how to use the Rust-native JWTBearer dependency to protect
routes with stateless token-based authentication.

Run:
    maturin develop && python examples/jwt_example.py

Test:
    # Get a token
    curl -X POST http://localhost:8000/token \
         -H "Content-Type: application/json" \
         -d '{"username": "alice", "password": "secret"}'

    # Access a protected route
    TOKEN="<paste token here>"
    curl http://localhost:8000/me -H "Authorization: Bearer $TOKEN"
    curl http://localhost:8000/admin -H "Authorization: Bearer $TOKEN"
"""

import time

from ignyx import Depends, HTTPException, Ignyx
from ignyx._core import JwtDecoder
from ignyx.security import JWTBearer

# ── Configuration ────────────────────────────────────────────────────────────

SECRET_KEY = "super-secret-key-change-in-production"
ALGORITHM = "HS256"
TOKEN_TTL_SECONDS = 3600

# One codec instance shared across the app — Rust object, zero Python overhead.
_codec = JwtDecoder(secret=SECRET_KEY, algorithm=ALGORITHM)

# Dependency — injects the decoded payload dict into any route that uses it.
jwt_required = JWTBearer(secret=SECRET_KEY, algorithm=ALGORITHM)

# ── Fake user database ───────────────────────────────────────────────────────

USERS = {
    "alice": {"password": "secret", "role": "admin"},
    "bob": {"password": "pass123", "role": "user"},
}

# ── App ──────────────────────────────────────────────────────────────────────

app = Ignyx(title="JWT Example", version="2.7.0")


@app.post("/token")
def login(body: dict) -> dict:
    """Issue a JWT for valid credentials."""
    username = body.get("username", "")
    password = body.get("password", "")
    user = USERS.get(username)
    if not user or user["password"] != password:
        raise HTTPException(401, "Invalid credentials")

    payload = {
        "sub": username,
        "role": user["role"],
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    token = _codec.encode(payload)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/me")
def me(payload: dict = Depends(jwt_required)) -> dict:
    """Return the token's subject.  Protected — requires a valid JWT."""
    return {"username": payload.get("sub"), "role": payload.get("role")}


@app.get("/admin")
def admin_only(payload: dict = Depends(jwt_required)) -> dict:
    """Admin-only endpoint — demonstrates payload inspection inside the route."""
    if payload.get("role") != "admin":
        raise HTTPException(403, "Admin access required")
    return {"message": f"Welcome, admin {payload.get('sub')}!"}


@app.get("/public")
def public() -> dict:
    """This route needs no token."""
    return {"message": "Anyone can see this"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
