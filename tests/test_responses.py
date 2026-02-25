import httpx

def test_html_response(app_server):
    r = httpx.get(f"{app_server}/html")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<h1>Hello</h1>" in r.text

def test_redirect_response(app_server):
    r = httpx.get(f"{app_server}/redirect", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "/health"

def test_cookie_set(app_server):
    r = httpx.get(f"{app_server}/cookie-set")
    assert r.status_code == 200
    assert "set-cookie" in r.headers

def test_cookie_read(app_server):
    r = httpx.get(f"{app_server}/cookie-read",
        headers={"Cookie": "test_cookie=hello"})
    assert r.status_code == 200
    assert r.json()["cookie"] == "hello"
