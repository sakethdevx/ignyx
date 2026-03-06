from ignyx import Ignyx, Depends, HTTPException
from ignyx.testclient import TestClient
from ignyx.depends import BackgroundTask
from ignyx.request import Request
import time

def test_depends_basic():
    app = Ignyx()
    def get_token(request: Request):
        return request.headers.get("Authorization", "")
        
    @app.get("/")
    def index(token=Depends(get_token)):
        return {"token": token}
        
    client = TestClient(app)
    r = client.get("/", headers={"Authorization": "Bearer 123"})
    assert r.json() == {"token": "Bearer 123"}

def test_depends_raises():
    app = Ignyx()
    def check_user():
        raise HTTPException(401, "unauthorized")
        
    @app.get("/")
    def index(user=Depends(check_user)):
        return "ok"
        
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 401

def test_depends_cache():
    app = Ignyx()
    calls = {"count": 0}
    
    def side_effect():
        calls["count"] += 1
        return calls["count"]
        
    @app.get("/")
    def index(v1=Depends(side_effect), v2=Depends(side_effect)):
        return {"v1": v1, "v2": v2}
        
    client = TestClient(app)
    r = client.get("/")
    assert r.json() == {"v1": 1, "v2": 1}
    assert calls["count"] == 1

def test_background_task():
    app = Ignyx()
    results = []
    
    def do_work(msg: str):
        time.sleep(0.1)
        results.append(msg)
        
    @app.post("/")
    def index():
        task = BackgroundTask(do_work, "done")
        return {"status": "accepted"}, 202, {}, task
        
    client = TestClient(app)
    r = client.post("/")
    assert r.status_code == 202
    assert results == []  # Not done yet
    time.sleep(0.8)  # Wait for background task to execute
    assert results == ["done"]


def test_shared_subdependency_cached_per_request():
    """Prove that a shared sub-dependency is evaluated exactly once per request.

    Dependency graph:
        get_db (counter) ← get_user(db) ← handler
                         ← get_settings(db) ← handler

    get_db must be called exactly once; both parents receive the same value.
    """
    app = Ignyx()
    calls = {"count": 0}

    def get_db():
        calls["count"] += 1
        return f"db-conn-{calls['count']}"

    def get_user(db=Depends(get_db)):
        return {"user": "alice", "db": db}

    def get_settings(db=Depends(get_db)):
        return {"theme": "dark", "db": db}

    @app.get("/")
    def index(user=Depends(get_user), settings=Depends(get_settings)):
        return {"user": user, "settings": settings}

    client = TestClient(app)

    # First request
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert calls["count"] == 1  # get_db called exactly once
    assert data["user"]["db"] == "db-conn-1"
    assert data["settings"]["db"] == "db-conn-1"  # Same cached value

    # Second request — fresh cache, counter increments to 2
    r2 = client.get("/")
    assert r2.status_code == 200
    data2 = r2.json()
    assert calls["count"] == 2  # One new call for the new request
    assert data2["user"]["db"] == "db-conn-2"
    assert data2["settings"]["db"] == "db-conn-2"


def test_depends_no_cache():
    """Prove that use_cache=False forces re-evaluation of a dependency."""
    app = Ignyx()
    calls = {"count": 0}

    def get_db():
        calls["count"] += 1
        return calls["count"]

    @app.get("/")
    def index(
        v1=Depends(get_db, use_cache=False),
        v2=Depends(get_db, use_cache=False),
    ):
        return {"v1": v1, "v2": v2}

    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert calls["count"] == 2  # Called twice — no caching
    assert r.json() == {"v1": 1, "v2": 2}

