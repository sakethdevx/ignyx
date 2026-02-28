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
