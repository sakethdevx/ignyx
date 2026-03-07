import os
from ignyx import Ignyx, Request
from ignyx.middleware import SessionMiddleware

app = Ignyx()

# Generate a random 32-byte secret key for the example,
# or provide a static one.
SECRET_KEY = os.urandom(32).hex()

# Secure the app with stateful, tamper-proof session cookies powered by Rust AES-GCM
app.add_middleware(SessionMiddleware(secret_key=SECRET_KEY))

@app.get("/")
def home(request: Request):
    """
    Reads the 'counter' from the encrypted session cookie,
    increments it, and returns the result.
    
    If the cookie doesn't exist or is tampered with, 
    the session starts fresh.
    """
    # session is just a normal Python dictionary
    current_count = request.session.get("counter", 0)
    
    new_count = current_count + 1
    
    # modify the dictionary; Ignyx natively encrypts this into a Set-Cookie header
    request.session["counter"] = new_count
    
    return {
        "message": "Welcome to the Session Example!",
        "visits": new_count
    }

@app.post("/reset")
def reset_session(request: Request):
    """
    Clears the entire session dictionary. Ignyx will natively
    delete the session cookie.
    """
    request.session.clear()
    return {"message": "Session has been reset!"}

if __name__ == "__main__":
    app.run("127.0.0.1", 8000)
