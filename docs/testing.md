# Testing

Ignyx provides a `TestClient` that allows you to test your application without starting a real HTTP server. This makes your tests significantly faster and easier to run in CI/CD environments.

## Overview

The `TestClient` uses an internal dispatch mechanism to call your route handlers directly, bypassing the network stack while still executing all middleware and dependency injection logic.

## Basic Example

Use the `TestClient` to verify the response of a simple GET route.

```python
from ignyx import Ignyx
from ignyx.testclient import TestClient

app = Ignyx()

@app.get("/health")
def health():
    return {"status": "ok"}

def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

## Testing POST with JSON Body

Pass data to the `json` parameter to send a JSON-encoded body.

```python
def test_create_user():
    client = TestClient(app)
    payload = {"name": "Saketh", "age": 25}
    response = client.post("/users", json=payload)
    assert response.status_code == 201
    assert response.json()["name"] == "Saketh"
```

## Testing File Uploads

You can test multipart file uploads by passing a dictionary to the `files` parameter.

```python
def test_upload():
    client = TestClient(app)
    files = {"file": ("test.txt", b"hello world", "text/plain")}
    response = client.post("/upload", files=files)
    assert response.status_code == 200
```

## Overriding Dependencies

One of the most powerful features of the `TestClient` is the ability to override dependencies during tests.

```python
def get_db():
    return real_db_connection

def test_with_mock_db():
    def mock_db():
        return {"data": "mocked"}
    
    app.dependency_overrides[get_db] = mock_db
    client = TestClient(app)
    
    response = client.get("/data")
    assert response.json()["data"] == "mocked"
```

## Testing WebSockets

The `TestClient` also supports testing WebSockets using a context manager.

```python
def test_websocket():
    client = TestClient(app)
    with client.websocket_connect("/ws") as ws:
        ws.send_text("Hello")
        data = ws.receive_text()
        assert data == "Echo: Hello"
```

## API Reference

### `TestClient(app)`
Initialize the test client with your Ignyx app.

### `client.get(url, headers=None, cookies=None)`
Send a GET request.

### `client.post(url, json=None, data=None, files=None, headers=None, cookies=None)`
Send a POST request.

### `client.websocket_connect(url)`
Connect to a WebSocket endpoint. Returns a context manager.
