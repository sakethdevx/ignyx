
def test_html_response(client):
    r = client.get("/html")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<h1>Hello</h1>" in r.text

def test_redirect_response(client):
    r = client.get("/redirect", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "/health"

def test_cookie_set(client):
    r = client.get("/cookie-set")
    assert r.status_code == 200
    assert "set-cookie" in r.headers

def test_cookie_read(client):
    r = client.get("/cookie-read",
        headers={"Cookie": "test_cookie=hello"})
    assert r.status_code == 200
    assert r.json()["cookie"] == "hello"
