import pytest
from ignyx import Ignyx, Request
from ignyx.testclient import TestClient
from ignyx.middleware import SessionMiddleware

SECRET_KEY = "super-secret-32-byte-key-here-12"

@pytest.fixture
def session_app():
    app = Ignyx()
    app.add_middleware(SessionMiddleware(secret_key=SECRET_KEY))

    @app.get("/login")
    def login(request: Request):
        # Set session data
        request.session["user_id"] = 123
        request.session["username"] = "tester"
        return {"status": "logged_in"}

    @app.get("/profile")
    def profile(request: Request):
        # Read session data
        if "user_id" in request.session:
            return {"user": request.session["username"]}
        return {"error": "unauthorized"}, 401
        
    @app.get("/logout")
    def logout(request: Request):
        # Clear session
        request.session.clear()
        return {"status": "logged_out"}

    return app

def test_session_lifecycle(session_app):
    client = TestClient(session_app)
    
    # 1. Start clean, profile should be unauthorized
    response = client.get("/profile")
    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"
    
    # 2. Login
    response = client.get("/login")
    assert response.status_code == 200
    
    # Extract the cookie header from the response
    cookie = response.headers.get("set-cookie", "")
    assert "session=" in cookie
    assert "HttpOnly" in cookie
    
    # Extract just the cookie value for subsequent requests
    # In realistic tests, TestClient manages cookies natively.
    session_cookie = cookie.split(";")[0]
    
    # 3. Access profile with the cookie set
    response = client.get("/profile", headers={"cookie": session_cookie})
    assert response.status_code == 200
    assert response.json()["user"] == "tester"
    
    # 4. Logout
    response = client.get("/logout", headers={"cookie": session_cookie})
    assert response.status_code == 200
    
    clear_cookie = response.headers.get("set-cookie", "")
    assert "Max-Age=0" in clear_cookie
