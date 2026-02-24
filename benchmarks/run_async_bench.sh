#!/bin/bash
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
/opt/homebrew/bin/python3.12 benchmarks/async_bench.py > /tmp/async_bench.log 2>&1 &
PID=$!
sleep 2

echo "=== SYNC PLAINTEXT ==="
wrk -t4 -c100 -d10s http://localhost:8000/sync

echo "=== ASYNC HANDLER ==="
wrk -t4 -c100 -d10s http://localhost:8000/async

echo "=== DYNAMIC ROUTING ==="
wrk -t4 -c100 -d10s http://localhost:8000/users/42

kill -9 $PID || true
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
