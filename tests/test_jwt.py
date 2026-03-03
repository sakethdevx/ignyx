"""Tests for Rust-native JWT encode/decode and JWTBearer dependency."""
import time

import pytest

from ignyx import Depends, HTTPException, Ignyx
from ignyx._core import JwtDecoder
from ignyx.security import JWTBearer
from ignyx.testclient import TestClient

SECRET = "test-secret-key"


# ── JwtDecoder (Rust codec) ──────────────────────────────────────────────────

def test_encode_decode_roundtrip():
    codec = JwtDecoder(secret=SECRET, algorithm="HS256", validate_exp=False)
    payload = {"sub": "alice", "role": "admin"}
    token = codec.encode(payload)
    assert isinstance(token, str)
    decoded = codec.decode(token)
    assert decoded["sub"] == "alice"
    assert decoded["role"] == "admin"


def test_decode_rejects_bad_signature():
    codec = JwtDecoder(secret=SECRET, algorithm="HS256", validate_exp=False)
    codec2 = JwtDecoder(secret="wrong-secret", algorithm="HS256", validate_exp=False)
    token = codec.encode({"sub": "alice"})
    with pytest.raises(ValueError):
        codec2.decode(token)


def test_decode_rejects_expired_token():
    codec = JwtDecoder(secret=SECRET, algorithm="HS256", validate_exp=True)
    token = codec.encode({"sub": "alice", "exp": int(time.time()) - 10})
    with pytest.raises(ValueError):
        codec.decode(token)


def test_decode_accepts_no_exp_when_disabled():
    codec = JwtDecoder(secret=SECRET, algorithm="HS256", validate_exp=False)
    token = codec.encode({"sub": "no-expiry"})
    decoded = codec.decode(token)
    assert decoded["sub"] == "no-expiry"


def test_payload_types_preserved():
    codec = JwtDecoder(secret=SECRET, algorithm="HS256", validate_exp=False)
    payload = {"flag": True, "count": 42, "score": 3.14, "name": "bob", "tags": ["x", "y"]}
    decoded = codec.decode(codec.encode(payload))
    assert decoded["flag"] is True
    assert decoded["count"] == 42
    assert abs(decoded["score"] - 3.14) < 0.001
    assert decoded["name"] == "bob"
    assert decoded["tags"] == ["x", "y"]


def test_unsupported_algorithm_raises():
    with pytest.raises(ValueError):
        JwtDecoder(secret=SECRET, algorithm="INVALID")


# ── JWTBearer dependency ─────────────────────────────────────────────────────

def _make_app(validate_exp: bool = False) -> tuple:
    codec = JwtDecoder(secret=SECRET, algorithm="HS256", validate_exp=False)
    bearer = JWTBearer(secret=SECRET, algorithm="HS256", validate_exp=validate_exp)

    app = Ignyx()

    @app.get("/protected")
    def protected(payload: dict = Depends(bearer)):
        return {"sub": payload.get("sub")}

    return app, codec


def test_jwt_bearer_valid_token():
    app, codec = _make_app()
    token = codec.encode({"sub": "alice"})
    client = TestClient(app)
    r = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["sub"] == "alice"


def test_jwt_bearer_missing_header_returns_401():
    app, _ = _make_app()
    client = TestClient(app)
    r = client.get("/protected")
    assert r.status_code == 401


def test_jwt_bearer_bad_token_returns_401():
    app, _ = _make_app()
    client = TestClient(app)
    r = client.get("/protected", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401


def test_jwt_bearer_wrong_scheme_returns_401():
    app, codec = _make_app()
    token = codec.encode({"sub": "alice"})
    client = TestClient(app)
    r = client.get("/protected", headers={"Authorization": f"Basic {token}"})
    assert r.status_code == 401
