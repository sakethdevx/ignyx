from ignyx import Ignyx
from ignyx.pagination import Page, paginate
from ignyx.request import Request
from ignyx.testclient import TestClient
from pydantic import BaseModel


class Item(BaseModel):
    id: int


class FakeQuery:
    def __init__(self, items):
        self._items = list(items)
        self._offset = 0
        self._limit = None

    def count(self):
        return len(self._items)

    def offset(self, value: int):
        clone = FakeQuery(self._items)
        clone._offset = value
        clone._limit = self._limit
        return clone

    def limit(self, value: int):
        clone = FakeQuery(self._items)
        clone._offset = self._offset
        clone._limit = value
        return clone

    def all(self):
        end = None if self._limit is None else self._offset + self._limit
        return self._items[self._offset:end]


def test_paginate_sequence_uses_request_query_params():
    app = Ignyx()

    @app.get("/items")
    def items(request: Request) -> Page[Item]:
        return paginate(request, [Item(id=i) for i in range(1, 6)])

    client = TestClient(app)
    response = client.get("/items?limit=2&offset=1")

    assert response.status_code == 200
    assert response.json() == {
        "total_items": 5,
        "next_page": "/items?limit=2&offset=3",
        "items": [{"id": 2}, {"id": 3}],
    }


def test_paginate_preserves_existing_query_params_in_next_page():
    app = Ignyx()

    @app.get("/search")
    def search(request: Request):
        return paginate(request, ["a", "b", "c", "d"], default_limit=2)

    client = TestClient(app)
    response = client.get("/search?tag=python&limit=2")

    assert response.status_code == 200
    assert response.json()["next_page"] == "/search?tag=python&limit=2&offset=2"


def test_paginate_supports_query_like_objects():
    app = Ignyx()

    @app.get("/users")
    def users(request: Request) -> Page[Item]:
        query = FakeQuery([Item(id=i) for i in range(1, 6)])
        return paginate(request, query, default_limit=2)

    client = TestClient(app)
    response = client.get("/users?offset=2")

    assert response.status_code == 200
    assert response.json() == {
        "total_items": 5,
        "next_page": "/users?offset=4&limit=2",
        "items": [{"id": 3}, {"id": 4}],
    }


def test_paginate_normalizes_invalid_values():
    app = Ignyx()

    @app.get("/numbers")
    def numbers(request: Request):
        return paginate(request, [1, 2, 3, 4], default_limit=3, max_limit=5)

    client = TestClient(app)
    response = client.get("/numbers?limit=nope&offset=-4")

    assert response.status_code == 200
    assert response.json() == {
        "total_items": 4,
        "next_page": "/numbers?limit=3&offset=3",
        "items": [1, 2, 3],
    }


def test_paginate_returns_no_next_page_at_end():
    app = Ignyx()

    @app.get("/final")
    def final_page(request: Request):
        return paginate(request, [1, 2], default_limit=2)

    client = TestClient(app)
    response = client.get("/final")

    assert response.status_code == 200
    assert response.json() == {
        "total_items": 2,
        "next_page": None,
        "items": [1, 2],
    }
