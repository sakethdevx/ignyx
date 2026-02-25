# Routing
Ignyx uses a high-performance Radix Tree router powered by the Rust `matchit` crate.
```python
@app.get("/users/{user_id}")
def get_user(user_id: int):
    return {"id": user_id}
```
