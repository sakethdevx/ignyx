from ignyx import Ignyx
from ignyx.testclient import TestClient

def test_openapi_json_200():
    app = Ignyx()
    @app.get("/test")
    def index(): return "ok"
    
    client = TestClient(app)
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert "openapi" in r.json()

def test_openapi_has_paths():
    app = Ignyx()
    @app.post("/submit")
    def submit(): return "ok"
    
    client = TestClient(app)
    r = client.get("/openapi.json")
    data = r.json()
    assert "/submit" in data["paths"]
    assert "post" in data["paths"]["/submit"]

def test_swagger_ui_200():
    app = Ignyx()
    client = TestClient(app)
    r = client.get("/docs")
    assert r.status_code == 200
    assert "swagger-ui" in r.text.lower()

def test_redoc_200():
    app = Ignyx()
    client = TestClient(app)
    r = client.get("/redoc")
    assert r.status_code == 200
    assert "redoc" in r.text.lower()

def test_path_in_schema():
    app = Ignyx()
    @app.get("/hello/{name}")
    def hello(name: str): return name
    
    client = TestClient(app)
    r = client.get("/openapi.json")
    data = r.json()
    assert "/hello/{name}" in data["paths"]
