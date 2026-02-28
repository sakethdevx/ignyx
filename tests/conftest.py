from ignyx import (Ignyx, Router, HTTPException)
from ignyx.responses import JSONResponse, HTMLResponse, RedirectResponse
from ignyx.request import Request
from ignyx.uploads import UploadFile
from ignyx.testclient import TestClient
from ignyx.security import OAuth2PasswordBearer
from ignyx.middleware import CORSMiddleware
from pydantic import BaseModel
import pytest

@pytest.fixture(scope="session")
def client():
    app = Ignyx()

    class User(BaseModel):
        name: str
        age: int

    @app.get("/health")
    def health(): return {"status": "ok"}

    @app.get("/users/{id}")
    def get_user(id: int): return {"id": id}

    @app.get("/search")
    def search(q: str, limit: int = 10): return {"q": q, "limit": limit}

    @app.post("/users")
    def create_user(body: User): return {"name": body.name, "age": body.age}

    @app.get("/html")
    def html(): return HTMLResponse("<h1>Hello</h1>")

    @app.get("/redirect")
    def redirect(): return RedirectResponse("/health", status_code=301)

    @app.get("/raise-404")
    def raise_404(): raise HTTPException(404, "not found here")

    @app.get("/cookie-set")
    def cookie_set():
        r = JSONResponse({"set": True})
        r.set_cookie("test_cookie", "hello", max_age=3600)
        return r

    @app.get("/cookie-read")
    def cookie_read(request: Request):
        val = request.cookies.get("test_cookie", "missing")
        return {"cookie": val}

    @app.post("/upload")
    async def upload(file: UploadFile):
        content = await file.read()
        return {"filename": file.filename, "size": file.size}

    @app.exception_handler(404)
    def not_found(request: Request, exc):
        return JSONResponse({"error": "not found"}, status_code=404)

    users_router = Router(prefix="/api/users")

    @users_router.get("/")
    def list_users(): return [{"id": 1}]

    @users_router.get("/{id}")
    def get_api_user(id: int): return {"api_user_id": id}

    app.include_router(users_router)
    return TestClient(app)
