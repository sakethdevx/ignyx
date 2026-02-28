from ignyx import Ignyx, HTTPException
from ignyx.testclient import TestClient

def test_http_exception_404():
    app = Ignyx()
    @app.get("/")
    def index(): raise HTTPException(404, "Not Found")
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 404
    assert r.json() == {"detail": "Not Found"}

def test_http_exception_403():
    app = Ignyx()
    @app.get("/")
    def index(): raise HTTPException(403, "Forbidden")
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 403
    assert r.json() == {"detail": "Forbidden"}

def test_http_exception_detail():
    app = Ignyx()
    @app.get("/")
    def index(): raise HTTPException(400, "Bad data")
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 400
    assert r.json()["detail"] == "Bad data"

def test_exception_handler_override():
    app = Ignyx()
    @app.get("/")
    def index(): raise HTTPException(400, "Bad data")
    
    @app.exception_handler(400)
    def handle_400(request, exc):
        return {"custom_error": True}, 418
        
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 418
    assert r.json() == {"custom_error": True}

def test_unhandled_exception():
    app = Ignyx()
    @app.get("/")
    def index(): 
        raise ValueError("Oops")
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 500
    # Expected internal server error JSON
    assert "detail" in r.json()
