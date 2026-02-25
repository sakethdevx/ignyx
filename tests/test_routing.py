import httpx

def test_basic_get(app_server):
    r = httpx.get(f"{app_server}/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_path_param_int(app_server):
    r = httpx.get(f"{app_server}/users/42")
    assert r.status_code == 200
    assert r.json() == {"id": 42}

def test_404_handler(app_server):
    r = httpx.get(f"{app_server}/doesnotexist")
    assert r.status_code == 404
    assert r.json()["error"] == "not found"

def test_query_params(app_server):
    r = httpx.get(f"{app_server}/search?q=ignyx&limit=5")
    assert r.status_code == 200
    assert r.json() == {"q": "ignyx", "limit": 5}

def test_router_prefix(app_server):
    r = httpx.get(f"{app_server}/api/users/")
    assert r.status_code == 200
    assert r.json() == [{"id": 1}]

def test_router_prefix_with_param(app_server):
    r = httpx.get(f"{app_server}/api/users/7")
    assert r.status_code == 200
    assert r.json() == {"api_user_id": 7}
