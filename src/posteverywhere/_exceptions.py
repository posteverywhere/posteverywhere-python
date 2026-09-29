"""Exceptions raised by the PostEverywhere client."""

from __future__ import annotations

from typing import Any, Dict, Optional

__all__ = [
    "PostEverywhereError",
    "APIConnectionError",
    "APIStatusError",
    "AuthenticationError",
    "PaymentRequiredError",
    "PermissionDeniedError",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    "RateLimitError",
    "APIError",
]


class PostEverywhereError(Exception):
    """Base class for every error this library raises."""

    def __init__(
        self,
        message: str,
        *,
        status: Optional[int] = None,
        code: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Any = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.request_id = request_id
        self.details = details
        self.body = body

    def __str__(self) -> str:
        parts = [self.message]
        if self.status is not None:
            parts.append(f"status={self.status}")
        if self.code:
            parts.append(f"code={self.code}")
        if self.request_id:
            parts.append(f"request_id={self.request_id}")
        return " | ".join(parts)


class APIConnectionError(PostEverywhereError):
    """The request did not get a response (network error or timeout)."""


class APIStatusError(PostEverywhereError):
    """The API returned an error response. Subclasses map to HTTP status codes."""


class AuthenticationError(APIStatusError):
    """401: the API key is missing, invalid, revoked or expired."""


class PaymentRequiredError(APIStatusError):
    """402: no active subscription, not enough AI credits, or an upgrade is needed."""


class PermissionDeniedError(APIStatusError):
    """403: the key lacks the scope for this call, or a quota blocks it."""


class NotFoundError(APIStatusError):
    """404: the resource does not exist in this workspace."""


class ConflictError(APIStatusError):
    """409: the resource is in a state that blocks this call."""


class ValidationError(APIStatusError):
    """400 or 422: the request was rejected. See ``code`` and ``details``."""


class RateLimitError(APIStatusError):
    """429: too many requests. ``retry_after`` is the wait in seconds, if sent."""

    def __init__(self, message: str, *, retry_after: Optional[float] = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class APIError(APIStatusError):
    """5xx, or any other unexpected status: a server-side failure."""
