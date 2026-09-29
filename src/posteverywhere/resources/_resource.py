from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Generic, TypeVar, Union
from urllib.parse import quote

_T = TypeVar("_T")

DateLike = Union[str, datetime]


class Resource(Generic[_T]):
    """Base for API resources.

    ``_T`` is the return type of the client's request function: plain data for
    ``PostEverywhere`` and an awaitable for ``AsyncPostEverywhere``. This lets
    one resource class serve both clients.
    """

    def __init__(self, request: Callable[..., _T]) -> None:
        self._request = request


def path_id(value: Union[str, int]) -> str:
    return quote(str(value), safe="")


def iso(value: Any) -> Any:
    """Turn a datetime into an ISO 8601 string. Other values pass through."""
    if isinstance(value, datetime):
        return value.isoformat()
    return value
