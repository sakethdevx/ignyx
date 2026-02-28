import threading
import time
import json
import httpx

class TestResponse:
    def __init__(self, status_code, body, headers):
        self.status_code = status_code
        self._body = body
        self.headers = headers
        self.text = body if isinstance(body, str) else body.decode("utf-8", errors="replace")
        
    def json(self):
        return json.loads(self.text)

class TestClient:
    def __init__(self, app):
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("", 0))
        port = s.getsockname()[1]
        s.close()

        self._app = app
        self._base = f"http://127.0.0.1:{port}"
        self._thread = threading.Thread(
            target=lambda: app.run(host="127.0.0.1", port=port), daemon=True
        )
        self._thread.start()
        
        # Poll until server is up
        for _ in range(30):
            try:
                # Use a raw socket to test if port is bound instead of httpx
                # to avoid logging 404/500 if we hit an endpoint.
                with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                    break
            except (ConnectionRefusedError, TimeoutError, OSError):
                time.sleep(0.1)

    def _request(self, method, path, **kwargs):
        resp = httpx.request(method, self._base + path, **kwargs)
        return TestResponse(resp.status_code, resp.content, resp.headers)

    def get(self, path, **kwargs): return self._request("GET", path, **kwargs)
    def post(self, path, **kwargs): return self._request("POST", path, **kwargs)
    def put(self, path, **kwargs): return self._request("PUT", path, **kwargs)
    def delete(self, path, **kwargs): return self._request("DELETE", path, **kwargs)
    def patch(self, path, **kwargs): return self._request("PATCH", path, **kwargs)
