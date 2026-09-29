"""Request and response logic shared by the sync and async clients."""

from __future__ import annotations

import email.utils
import os
import random
import time
from typing import Any, Dict, Mapping, Optional

import httpx

from ._exceptions import (
    APIError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PaymentRequiredError,
    PermissionDeniedError,
    PostEverywhereError,
    RateLimitError,
    ValidationError,
)
from ._version import __version__

DEFAULT_BASE_URL = "https://app.posteverywhere.ai/api/v1"
DEFAULT_TIMEOUT = 120.0  # AI generation can be slow
DEFAULT_MAX_RETRIES = 2
API_KEY_ENV = "POSTEVERYWHERE_API_KEY"
BASE_URL_ENV = "POSTEVERYWHERE_BASE_URL"

# Retrying these after a server error cannot create a duplicate.
IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "DELETE"})
MAX_RETRY_AFTER = 60.0
INITIAL_BACKOFF = 0.5
MAX_BACKOFF = 8.0


def resolve_api_key(api_key: Optional[str]) -> str:
    key = api_key or os.environ.get(API_KEY_ENV)
    if not key:
        raise PostEverywhereError(
            "No API key found. Pass api_key=... or set the "
            f"{API_KEY_ENV} environment variable. "
            "Create a key at https://app.posteverywhere.ai/developers"
        )
    return key


def resolve_base_url(base_url: Optional[str]) -> str:
    url = base_url or os.environ.get(BASE_URL_ENV) or DEFAULT_BASE_URL
    return url.rstrip("/")


def default_headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": f"posteverywhere-python/{__version__}",
    }


def clean(values: Mapping[str, Any]) -> Dict[str, Any]:
    """Drop keys whose value is None, so we only send what the caller set."""
    return {k: v for k, v in values.items() if v is not None}


def clean_params(values: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, bool):
            out[key] = "true" if value else "false"
        elif isinstance(value, (list, tuple)):
            out[key] = ",".join(str(v) for v in value)
        else:
            out[key] = value
    return out


def parse_retry_after(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            parsed = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        if parsed is None:
            return None
        seconds = parsed.timestamp() - time.time()
    return max(0.0, seconds)


def should_retry(method: str, response: Optional[httpx.Response], error: Optional[Exception]) -> bool:
    if response is not None:
        if response.status_code == 429:
            return True  # the request was refused, not processed
        if response.status_code >= 500:
            return method.upper() in IDEMPOTENT_METHODS
        return False
    if isinstance(error, httpx.ConnectError):
        return True  # never reached the server
    if isinstance(error, httpx.TransportError):
        return method.upper() in IDEMPOTENT_METHODS
    return False


def retry_delay(attempt: int, response: Optional[httpx.Response]) -> float:
    """Seconds to wait before retry number ``attempt`` (0-based)."""
    if response is not None:
        retry_after = parse_retry_after(response.headers.get("Retry-After"))
        if retry_after is not None:
            return min(retry_after, MAX_RETRY_AFTER)
    backoff = min(INITIAL_BACKOFF * (2 ** attempt), MAX_BACKOFF)
    return backoff * (0.75 + random.random() * 0.5)


def _parse_json(response: httpx.Response) -> Optional[Dict[str, Any]]:
    try:
        body = response.json()
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


def _error_for(response: httpx.Response, body: Optional[Dict[str, Any]]) -> PostEverywhereError:
    status = response.status_code
    error = (body or {}).get("error") or {}
    if not isinstance(error, dict):
        error = {"message": str(error)}
    meta = (body or {}).get("meta") or {}
    message = error.get("message") or f"Request failed with status {status}"
    kwargs: Dict[str, Any] = {
        "status": status,
        "code": error.get("code"),
        "request_id": meta.get("request_id") if isinstance(meta, dict) else None,
        "details": error.get("details"),
        "body": body,
    }
    if status == 401:
        return AuthenticationError(message, **kwargs)
    if status == 402:
        return PaymentRequiredError(message, **kwargs)
    if status == 403:
        return PermissionDeniedError(message, **kwargs)
    if status == 404:
        return NotFoundError(message, **kwargs)
    if status == 409:
        return ConflictError(message, **kwargs)
    if status in (400, 422):
        return ValidationError(message, **kwargs)
    if status == 429:
        retry_after = parse_retry_after(response.headers.get("Retry-After"))
        return RateLimitError(message, retry_after=retry_after, **kwargs)
    return APIError(message, **kwargs)


def process_response(response: httpx.Response) -> Any:
    """Unwrap the ``{data, error, meta}`` envelope, or raise the mapped error.

    A response with ``error: null`` and a ``data`` object is a success even when
    the status is not 2xx. ``POST /posts/bulk`` uses this: 207 when some items
    failed and 422 when all did, with per-item results in ``data``.
    """
    body = _parse_json(response)
    if body is not None and "data" in body and not body.get("error"):
        if response.is_success or body.get("data") is not None:
            return body["data"]
    if response.is_success and body is None:
        raise APIError(
            f"Expected a JSON response, got status {response.status_code}",
            status=response.status_code,
        )
    raise _error_for(response, body)


def build_request_kwargs(params: Optional[Mapping[str, Any]], json: Optional[Any]) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {}
    if params:
        kwargs["params"] = clean_params(params)
    if json is not None:
        kwargs["json"] = json
    return kwargs
