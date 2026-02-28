from ignyx import Ignyx
from ignyx.testclient import TestClient
from ignyx.middleware import Middleware, CORSMiddleware, RateLimitMiddleware
from ignyx.responses import PlainTextResponse
import time
import pytest

def test_cors_headers_present():
    app = Ignyx()
    app.add_middleware(CORSMiddleware(allow_origins=["*"], allow_headers=["*"], allow_methods=["*"]))
    
    @app.get("/")
    def index(): return "ok"
    
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "*"
    assert r.headers["access-control-allow-methods"] == "*"

def test_cors_preflight():
    app = Ignyx()
    app.add_middleware(CORSMiddleware(allow_origins=["http://example.com"], allow_methods=["GET"]))
    
    @app.get("/")
    def index(): return "ok"
    
    client = TestClient(app)
    r = client._request("OPTIONS", "/")
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://example.com"

def test_rate_limit():
    app = Ignyx()
    app.add_middleware(RateLimitMiddleware(requests=2, window=60))
    
    @app.get("/")
    def index(): return "ok"
    
    client = TestClient(app)
    r1 = client.get("/")
    assert r1.status_code == 200
    r2 = client.get("/")
    assert r2.status_code == 200
    r3 = client.get("/")
    assert r3.status_code == 429
    assert r3.headers["retry-after"] == "60"

def test_rate_limit_resets():
    app = Ignyx()
    app.add_middleware(RateLimitMiddleware(requests=1, window=1))
    
    @app.get("/")
    def index(): return "ok"
    
    client = TestClient(app)
    r1 = client.get("/")
    assert r1.status_code == 200
    r2 = client.get("/")
    assert r2.status_code == 429
    time.sleep(1.1)
    r3 = client.get("/")
    assert r3.status_code == 200

def test_custom_middleware_order():
    app = Ignyx()
    
    class MiddlewareA(Middleware):
        def before_request(self, req):
            req.headers["X-Trace"] = "A"
            return req
        def after_request(self, req, res):
            headers = res[2] if isinstance(res, tuple) and len(res) > 2 else {}
            headers["X-Response"] = headers.get("X-Response", "") + "A"
            if isinstance(res, tuple):
                return (res[0], res[1], headers)
            return (res, 200, headers)
            
    class MiddlewareB(Middleware):
        def before_request(self, req):
            req.headers["X-Trace"] += "B"
            return req
        def after_request(self, req, res):
            headers = res[2] if isinstance(res, tuple) and len(res) > 2 else {}
            headers["X-Response"] = headers.get("X-Response", "") + "B"
            if isinstance(res, tuple):
                return (res[0], res[1], headers)
            return (res, 200, headers)
            
    app.add_middleware(MiddlewareA())
    app.add_middleware(MiddlewareB())
    
    @app.get("/")
    def index(request): 
        return PlainTextResponse(request.headers.get("X-Trace", ""))
        
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert r.text == "AB"
    assert r.headers["x-response"] == "BA"
