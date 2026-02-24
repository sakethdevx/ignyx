"""Hello world test app for Ignyx."""
from ignyx import Ignyx

app = Ignyx()

@app.get("/")
def hello():
    return {"message": "Ignyx is live"}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
