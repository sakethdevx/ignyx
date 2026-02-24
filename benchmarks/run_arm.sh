#!/bin/bash
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
/opt/homebrew/bin/python3.12 benchmarks/minimal_arm.py > /tmp/minimal_arm.log 2>&1 &
PID=$!
sleep 2
wrk -t4 -c100 -d10s http://localhost:8000/plaintext
kill -9 $PID || true
