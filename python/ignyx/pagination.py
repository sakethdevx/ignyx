"""
Built-in pagination helpers for Ignyx APIs.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, Generic, TypeVar, cast
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Standard limit/offset pagination envelope."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    total_items: int = Field(ge=0)
    next_page: str | None = None
    items: list[T]


def paginate(
    request: Any,
    dataset: Any,
    *,
    default_limit: int = 50,
    max_limit: int | None = 100,
) -> Page[Any]:
    """
    Paginate a sequence or query-like object using ``limit`` and ``offset``
    query parameters from the request.
    """
    limit, offset = _extract_pagination_params(
        request,
        default_limit=default_limit,
        max_limit=max_limit,
    )
    total_items, items = _slice_dataset(dataset, limit=limit, offset=offset)
    return Page[Any](
        total_items=total_items,
        next_page=_build_next_page(request, limit=limit, offset=offset, total_items=total_items),
        items=items,
    )


def _extract_pagination_params(
    request: Any,
    *,
    default_limit: int,
    max_limit: int | None,
) -> tuple[int, int]:
    query_params = getattr(request, "query_params", {}) or {}

    limit = _coerce_int(query_params.get("limit"), fallback=default_limit)
    offset = _coerce_int(query_params.get("offset"), fallback=0)

    if limit < 0:
        limit = default_limit
    if offset < 0:
        offset = 0
    if max_limit is not None:
        limit = min(limit, max_limit)

    return limit, offset


def _coerce_int(value: Any, *, fallback: int) -> int:
    if value is None:
        return fallback
    if isinstance(value, list):
        value = value[0] if value else None
        if value is None:
            return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _slice_dataset(dataset: Any, *, limit: int, offset: int) -> tuple[int, list[Any]]:
    if _is_query_like(dataset):
        return _slice_query(dataset, limit=limit, offset=offset)

    if isinstance(dataset, Sequence):
        total_items = len(dataset)
        return total_items, list(dataset[offset : offset + limit])

    materialized = list(cast(Iterable[Any], dataset))
    total_items = len(materialized)
    return total_items, materialized[offset : offset + limit]


def _is_query_like(dataset: Any) -> bool:
    return not isinstance(dataset, Sequence) and (
        callable(getattr(dataset, "limit", None)) or callable(getattr(dataset, "offset", None))
    )


def _slice_query(dataset: Any, *, limit: int, offset: int) -> tuple[int, list[Any]]:
    total_items = _count_query(dataset)
    query = dataset

    offset_fn = getattr(query, "offset", None)
    if callable(offset_fn):
        query = offset_fn(offset)

    limit_fn = getattr(query, "limit", None)
    if callable(limit_fn):
        query = limit_fn(limit)

    all_fn = getattr(query, "all", None)
    if callable(all_fn):
        items = list(all_fn())
    else:
        fetchall_fn = getattr(query, "fetchall", None)
        if callable(fetchall_fn):
            items = list(fetchall_fn())
        else:
            items = list(query)

    return total_items, items


def _count_query(dataset: Any) -> int:
    count_fn = getattr(dataset, "count", None)
    if callable(count_fn):
        return int(count_fn())

    materialized = list(cast(Iterable[Any], dataset))
    return len(materialized)


def _build_next_page(
    request: Any,
    *,
    limit: int,
    offset: int,
    total_items: int,
) -> str | None:
    if limit <= 0 or offset + limit >= total_items:
        return None

    params = dict(getattr(request, "query_params", {}) or {})
    params["limit"] = limit
    params["offset"] = offset + limit

    query_string = urlencode(params, doseq=True)
    path = getattr(request, "path", "")
    if not query_string:
        return path or None
    return f"{path}?{query_string}"
