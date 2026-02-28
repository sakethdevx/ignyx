from ignyx import Ignyx
from ignyx.testclient import TestClient

def test_startup_called():
    app = Ignyx()
    app.state.started = False
    
    @app.on_startup
    def start():
        app.state.started = True
        
    @app.get("/")
    def index(): return app.state.started
    
    # TestClient calls app.run() in thread, which calls on_startup
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() is True

def test_startup_async():
    app = Ignyx()
    app.state.async_started = False
    
    @app.on_startup
    async def start():
        app.state.async_started = True
        
    @app.get("/")
    def index(): return app.state.async_started
    
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() is True

def test_state():
    app = Ignyx()
    app.state.foo = "bar"
    
    @app.get("/")
    def index(): return app.state.foo
    
    client = TestClient(app)
    r = client.get("/")
    assert r.text == '"bar"'
