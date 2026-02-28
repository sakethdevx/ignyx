
def test_basic_get(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_path_param_int(client):
    r = client.get("/users/42")
    assert r.status_code == 200
    assert r.json() == {"id": 42}

def test_404_handler(client):
    r = client.get("/doesnotexist")
    assert r.status_code == 404
    assert r.json()["error"] == "not found"

def test_query_params(client):
    r = client.get("/search?q=ignyx&limit=5")
    assert r.status_code == 200
    assert r.json() == {"q": "ignyx", "limit": 5}

def test_router_prefix(client):
    r = client.get("/api/users/")
    assert r.status_code == 200
    assert r.json() == [{"id": 1}]

def test_router_prefix_with_param(client):
    r = client.get("/api/users/7")
    assert r.status_code == 200
    assert r.json() == {"api_user_id": 7}
