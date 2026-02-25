# Quickstart
Install Ignyx via pip:
```bash
pip install ignyx
```
Create a basic app:
```python
from ignyx import Ignyx
app = Ignyx()

@app.get("/")
async def root():
    return {"message": "Ignited!"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
```
