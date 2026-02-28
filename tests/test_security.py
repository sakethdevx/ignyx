from ignyx import Ignyx, Depends
from ignyx.testclient import TestClient
from ignyx.security import OAuth2PasswordBearer, APIKeyHeader, HTTPBasic

def test_oauth2_valid():
    app = Ignyx()
    oauth2 = OAuth2PasswordBearer("/token")
    @app.get("/")
    def index(token: str = Depends(oauth2)):
        return {"token": token}
    client = TestClient(app)
    r = client.get("/", headers={"Authorization": "Bearer supersecret"})
    assert r.status_code == 200
    assert r.json() == {"token": "supersecret"}

def test_oauth2_missing():
    app = Ignyx()
    oauth2 = OAuth2PasswordBearer("/token")
    @app.get("/")
    def index(token: str = Depends(oauth2)): return "ok"
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"

def test_oauth2_wrong_scheme():
    app = Ignyx()
    oauth2 = OAuth2PasswordBearer("/token")
    @app.get("/")
    def index(token: str = Depends(oauth2)): return "ok"
    client = TestClient(app)
    r = client.get("/", headers={"Authorization": "Basic abc"})
    assert r.status_code == 401

def test_apikey_valid():
    app = Ignyx()
    api_key = APIKeyHeader("X-API-KEY")
    @app.get("/")
    def index(key: str = Depends(api_key)): return {"key": key}
    client = TestClient(app)
    r = client.get("/", headers={"X-API-KEY": "mykey123"})
    assert r.status_code == 200
    assert r.json() == {"key": "mykey123"}

def test_apikey_missing():
    app = Ignyx()
    api_key = APIKeyHeader("X-API-KEY")
    @app.get("/")
    def index(key: str = Depends(api_key)): return "ok"
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 403

def test_httpbasic_valid():
    app = Ignyx()
    basic = HTTPBasic()
    @app.get("/")
    def index(creds=Depends(basic)): return creds
    client = TestClient(app)
    # user:pass base64 encoded is dXNlcjpwYXNz
    r = client.get("/", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert r.status_code == 200
    assert r.json() == {"username": "user", "password": "pass"}
