#!/bin/bash
set -e

echo "Ensuring FastAPI is installed natively..."
/opt/homebrew/bin/python3.12 -m pip install fastapi uvicorn --quiet --break-system-packages

echo "Starting Servers..."
# Start Ignyx natively
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
/opt/homebrew/bin/python3.12 benchmarks/native_ignyx_app.py > /tmp/ignyx_bench.log 2>&1 &
IGNYX_PID=$!

# Start FastAPI natively
lsof -ti :8001 | xargs kill -9 2>/dev/null || true
/opt/homebrew/bin/python3.12 benchmarks/native_fastapi_app.py > /tmp/fastapi_bench.log 2>&1 &
FASTAPI_PID=$!

sleep 3

echo "=== IGNYX PLAINTEXT (native ARM) ==="
wrk -t4 -c100 -d10s http://localhost:8000/plaintext

echo "=== FASTAPI PLAINTEXT ==="
wrk -t4 -c100 -d10s http://localhost:8001/plaintext

echo "=== IGNYX DYNAMIC ==="
wrk -t4 -c100 -d10s http://localhost:8000/users/42

echo "=== FASTAPI DYNAMIC ==="
wrk -t4 -c100 -d10s http://localhost:8001/users/42

echo "=== IGNYX JSON ==="
wrk -t4 -c100 -d10s -s benchmarks/post.lua http://localhost:8000/users

echo "=== FASTAPI JSON ==="
wrk -t4 -c100 -d10s -s benchmarks/post.lua http://localhost:8001/users

# Cleanup
echo "Killing servers..."
kill -9 $IGNYX_PID $FASTAPI_PID || true
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
lsof -ti :8001 | xargs kill -9 2>/dev/null || true
