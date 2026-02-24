import time
import multiprocessing
import requests
from ignyx import Ignyx, Request

app = Ignyx()

@app.get("/hello")
def hello():
    return {"message": "Hello World!"}

@app.post("/heavy")
def heavy_endpoint(body: dict, request: Request):
    auth = request.headers.get("authorization")
    if not auth:
        return {"error": "Unauthorized"}, 401
    
    # Simulate realistic query parameter defaults
    limit = int(request.query_params.get("limit", 10))
    sort = request.query_params.get("sort", "asc")
    
    return {
        "received_items": len(body.get("items", [])),
        "limit": limit,
        "sort": sort,
        "auth_token": auth
    }, 201

def run_server():
    app.run(port=8000)

if __name__ == "__main__":
    print("Starting Ignyx server for benchmark...")
    server_process = multiprocessing.Process(target=run_server)
    server_process.start()
    
    time.sleep(2)  # Wait for server to start
    
    print("\n--- Running Baseline (/hello) ---")
    start_time = time.time()
    for _ in range(1000):
        requests.get("http://localhost:8000/hello")
    baseline_time = time.time() - start_time
    print(f"1000 baseline requests took: {baseline_time:.4f}s")
    
    print("\n--- Running Heavy Pipeline (/heavy) ---")
    payload = {"items": [{"id": i, "name": f"Item {i}"} for i in range(50)]}
    headers = {"Authorization": "Bearer benchmark-token"}
    
    start_time = time.time()
    for _ in range(1000):
        resp = requests.post("http://localhost:8000/heavy?limit=50&sort=desc", json=payload, headers=headers)
        assert resp.status_code == 201
    heavy_time = time.time() - start_time
    print(f"1000 heavy pipeline requests took: {heavy_time:.4f}s")
    
    print(f"\nTotal Overhead of Priority 1 Pipeline vs Baseline: +{((heavy_time - baseline_time) / baseline_time * 100):.2f}%")
    
    server_process.terminate()
    server_process.join()
