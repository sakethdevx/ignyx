# Benchmarks
Ignyx is designed to be genuinely faster than existing frameworks by optimizing the entire request lifecycle.

| Endpoint | Ignyx | FastAPI | Speedup |
| :--- | :--- | :--- | :--- |
| `/plaintext` | 53,886 req/s | 6,193 req/s | **8.70x** |
| `/users/{id}` | 48,988 req/s | 5,597 req/s | **8.75x** |
| `/users` (JSON) | 44,178 req/s | 5,200 req/s | **8.49x** |
