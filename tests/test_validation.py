
def test_pydantic_valid(client):
    r = client.post("/users",
        json={"name": "Saketh", "age": 22})
    assert r.status_code == 200
    assert r.json() == {"name": "Saketh", "age": 22}

def test_pydantic_invalid(client):
    r = client.post("/users",
        json={"name": "Saketh", "age": "notanumber"})
    assert r.status_code == 422

def test_pydantic_missing_field(client):
    r = client.post("/users",
        json={"name": "Saketh"})
    assert r.status_code == 422
