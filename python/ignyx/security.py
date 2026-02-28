from ignyx.exceptions import HTTPException
import base64

class OAuth2PasswordBearer:
    def __init__(self, token_url: str):
        self.token_url = token_url
        
    def __call__(self, request) -> str:
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            raise HTTPException(
                401, 
                "Not authenticated",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return auth[7:]

class APIKeyHeader:
    def __init__(self, name: str, auto_error: bool = True):
        self.name = name
        self.auto_error = auto_error
        
    def __call__(self, request) -> str:
        key = request.headers.get(self.name.lower())
        if not key and self.auto_error:
            raise HTTPException(403, "API key required")
        return key

class HTTPBasic:
    def __call__(self, request):
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Basic "):
            raise HTTPException(
                401, 
                "Not authenticated",
                headers={"WWW-Authenticate": "Basic"}
            )
        try:
            decoded = base64.b64decode(auth[6:]).decode("utf-8")
        except Exception:
            raise HTTPException(401, "Invalid authentication credentials")
        
        username, _, password = decoded.partition(":")
        return {"username": username, "password": password}
