#!/usr/bin/env python3
"""
Ignyx Benchmark Suite — TechEmpower-style benchmarks.
Compares Ignyx against FastAPI, Starlette, and Flask.

Usage: python3 benchmarks/bench.py
"""

import subprocess
import time
import signal
import os
import sys
import json

WRK_CMD = "wrk -t4 -c100 -d10s"
HOST = "http://localhost"
PORT = 8000

FRAMEWORKS = {}

# ---- Framework server scripts ----

IGNYX_SCRIPT = '''
from ignyx import Ignyx
import json

app = Ignyx()

@app.get("/plaintext")
def plaintext():
    return "Hello, World!"

@app.get("/json")
def json_endpoint():
    return {"message": "Hello, World!"}

@app.get("/")
def hello():
    return {"message": "Hello, World!"}

app.run(host="0.0.0.0", port={port})
'''

FASTAPI_SCRIPT = '''
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse, JSONResponse

app = FastAPI()

@app.get("/plaintext")
def plaintext():
    return PlainTextResponse("Hello, World!")

@app.get("/json")
def json_endpoint():
    return {{"message": "Hello, World!"}}

@app.get("/")
def hello():
    return {{"message": "Hello, World!"}}
'''

STARLETTE_SCRIPT = '''
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, JSONResponse
from starlette.routing import Route

def plaintext(request):
    return PlainTextResponse("Hello, World!")

def json_endpoint(request):
    return JSONResponse({{"message": "Hello, World!"}})

def hello(request):
    return JSONResponse({{"message": "Hello, World!"}})

app = Starlette(routes=[
    Route("/plaintext", plaintext),
    Route("/json", json_endpoint),
    Route("/", hello),
])
'''

FLASK_SCRIPT = '''
from flask import Flask, jsonify

app = Flask(__name__)

@app.get("/plaintext")
def plaintext():
    return "Hello, World!"

@app.get("/json")
def json_endpoint():
    return jsonify(message="Hello, World!")

@app.get("/")
def hello():
    return jsonify(message="Hello, World!")
'''


def write_temp_script(name, content, port=8000):
    """Write a temporary server script."""
    path = f"/tmp/bench_{name}.py"
    with open(path, "w") as f:
        f.write(content.format(port=port))
    return path


def start_server(name, port=8000):
    """Start a framework server and return the process."""
    python = "/opt/anaconda3/bin/python3"
    
    if name == "ignyx":
        script = write_temp_script(name, IGNYX_SCRIPT, port)
        proc = subprocess.Popen(
            [python, script],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    elif name == "fastapi":
        script = write_temp_script(name, FASTAPI_SCRIPT, port)
        proc = subprocess.Popen(
            [python, "-m", "uvicorn", f"bench_{name}:app",
             "--host", "0.0.0.0", "--port", str(port)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd="/tmp"
        )
    elif name == "starlette":
        script = write_temp_script(name, STARLETTE_SCRIPT, port)
        proc = subprocess.Popen(
            [python, "-m", "uvicorn", f"bench_{name}:app",
             "--host", "0.0.0.0", "--port", str(port)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd="/tmp"
        )
    elif name == "flask":
        script = write_temp_script(name, FLASK_SCRIPT, port)
        env = os.environ.copy()
        env["FLASK_APP"] = script
        proc = subprocess.Popen(
            [python, "-m", "flask", "run", "--host", "0.0.0.0", "--port", str(port)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=env
        )
    else:
        raise ValueError(f"Unknown framework: {name}")
    
    # Wait for server to start
    time.sleep(3)
    return proc


def run_wrk(endpoint, port=8000):
    """Run wrk benchmark and return results."""
    url = f"http://localhost:{port}{endpoint}"
    result = subprocess.run(
        f"wrk -t4 -c100 -d10s {url}",
        shell=True, capture_output=True, text=True
    )
    output = result.stdout
    
    # Parse req/sec from wrk output
    for line in output.split("\n"):
        if "Requests/sec" in line:
            req_sec = float(line.split(":")[1].strip())
            return req_sec
    return 0.0


def kill_server(proc):
    """Kill a server process."""
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except:
        proc.kill()
        proc.wait()


def benchmark_framework(name, port=8000):
    """Benchmark a single framework."""
    print(f"\n{'='*50}")
    print(f"  Benchmarking: {name.upper()}")
    print(f"{'='*50}")
    
    proc = start_server(name, port)
    
    # Wait a bit more for startup
    time.sleep(2)
    
    results = {}
    
    endpoints = {
        "Plaintext": "/plaintext",
        "JSON": "/json",
    }
    
    for test_name, endpoint in endpoints.items():
        print(f"\n  Running {test_name} test...")
        req_sec = run_wrk(endpoint, port)
        results[test_name] = req_sec
        print(f"  {test_name}: {req_sec:,.0f} req/sec")
    
    kill_server(proc)
    time.sleep(1)
    
    return results


def main():
    print("=" * 60)
    print("  🔥 IGNYX BENCHMARK SUITE")  
    print("  TechEmpower-style framework comparison")
    print("=" * 60)
    
    all_results = {}
    
    frameworks_to_test = ["ignyx", "fastapi", "starlette", "flask"]
    
    for fw in frameworks_to_test:
        try:
            results = benchmark_framework(fw)
            all_results[fw] = results
        except Exception as e:
            print(f"  ❌ Error benchmarking {fw}: {e}")
            all_results[fw] = {"Plaintext": 0, "JSON": 0}
    
    # Print summary
    print("\n\n" + "=" * 70)
    print("  📊 BENCHMARK RESULTS")
    print("=" * 70)
    print(f"\n  {'Framework':<15} {'Plaintext':>15} {'JSON':>15}")
    print(f"  {'-'*15} {'-'*15} {'-'*15}")
    
    for fw, results in all_results.items():
        pt = results.get("Plaintext", 0)
        js = results.get("JSON", 0)
        emoji = "🔥" if fw == "ignyx" else "⚡" if fw in ("fastrapi",) else "🐢"
        print(f"  {emoji} {fw:<13} {pt:>12,.0f}/s {js:>12,.0f}/s")
    
    # Save results as JSON
    with open("benchmarks/results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n  Results saved to benchmarks/results.json")
    print("=" * 70)


if __name__ == "__main__":
    main()
