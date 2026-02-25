# Validation
Ignyx features native Pydantic v2 integration for high-speed schema enforcement.
```python
from pydantic import BaseModel
class Item(BaseModel):
    name: str
    price: float

@app.post("/items")
def create_item(body: Item):
    return body
```
