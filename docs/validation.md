# Validation

Ignyx leverages the power of Pydantic v2 for high-speed data validation and schema enforcement. This allows you to define the structure of your data once and have Ignyx handle the validation and parsing automatically.

## Overview

When you type-hint a route handler parameter with a Pydantic `BaseModel`, Ignyx automatically:
1. Reads the request body.
2. Validates the data against the model.
3. Returns a `422 Unprocessable Entity` response if validation fails.
4. Passes the parsed model instance to your handler.

## Basic Example

Define a model and use it in your route.

```python
from pydantic import BaseModel
from ignyx import Ignyx

app = Ignyx()

class User(BaseModel):
    name: str
    age: int

@app.post("/users")
def create_user(user: User):
    return {"message": f"Hello {user.name}, you are {user.age}!"}
```

## Nested Models

You can nest models to represent complex data structures.

```python
class Address(BaseModel):
    city: str
    country: str

class Profile(BaseModel):
    username: str
    address: Address

@app.post("/profile")
def update_profile(profile: Profile):
    return {"city": profile.address.city}
```

## Optional Fields

Use Python's type system to define optional fields.

```python
from typing import Optional

class Item(BaseModel):
    name: str
    description: Optional[str] = None # Or use name: str | None = None
    price: float
```

## Validation Errors

If a client sends invalid data, Ignyx automatically returns a structured `422` error response.

**Request:**
```json
{
    "name": "Saketh",
    "age": "invalid_age"
}
```

**Response (422):**
```json
{
    "detail": [
        {
            "loc": ["body", "age"],
            "msg": "Input should be a valid integer",
            "type": "int_parsing"
        }
    ]
}
```

## Field Validators

You can add custom validation logic using Pydantic's `@field_validator`.

```python
from pydantic import BaseModel, field_validator

class Signup(BaseModel):
    username: str
    password: str

    @field_validator('username')
    @classmethod
    def username_must_be_long(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError('Username is too short')
        return v
```

## API Reference

Ignyx supports any Pydantic `BaseModel`. For full documentation on model features, see the [Pydantic Documentation](https://docs.pydantic.dev/).
