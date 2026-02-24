import time
from ignyx import Ignyx
from ignyx.depends import BackgroundTask
from ignyx.middleware import CORSMiddleware

app = Ignyx()
app.add_middleware(CORSMiddleware(allow_origins=["http://localhost:3000"]))

def log_request():
    time.sleep(0.1)
    print("Background task executed!", flush=True)

@app.post("/email")
def email(task: BackgroundTask):
    task.add(log_request)
    return {"status": "queued"}

if __name__ == "__main__":
    app.run(port=8000)
