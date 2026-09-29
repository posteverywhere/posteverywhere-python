"""Sync and async PostEverywhere clients."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Mapping, Optional

import httpx

from . import _base
from ._exceptions import APIConnectionError
from .resources import AI, Accounts, Analytics, Campaigns, Media, Posts, Webhooks

__all__ = ["PostEverywhere", "AsyncPostEverywhere"]


class PostEverywhere:
    """Synchronous client for the PostEverywhere v1 API.

    Args:
        api_key: Your ``pe_live_...`` key. Falls back to ``POSTEVERYWHERE_API_KEY``.
        base_url: API root. Defaults to ``https://app.posteverywhere.ai/api/v1``.
        timeout: Seconds before a request times out.
        max_retries: How many times to retry a 429, a 5xx on a safe method,
            or a connection error.
        http_client: Optional ``httpx.Client`` to use (for proxies or tests).
    """

    accounts: Accounts[Any]
    posts: Posts[Any]
    media: Media[Any]
    ai: AI[Any]
    analytics: Analytics[Any]
    campaigns: Campaigns[Any]
    webhooks: Webhooks[Any]

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = _base.DEFAULT_TIMEOUT,
        max_retries: int = _base.DEFAULT_MAX_RETRIES,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self.api_key = _base.resolve_api_key(api_key)
        self.base_url = _base.resolve_base_url(base_url)
        self.timeout = timeout
        self.max_retries = max_retries
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=timeout)
        self._headers = _base.default_headers(self.api_key)

        self.accounts = Accounts(self._request)
        self.posts = Posts(self._request)
        self.media = Media(self._request)
        self.ai = AI(self._request)
        self.analytics = Analytics(self._request)
        self.campaigns = Campaigns(self._request)
        self.webhooks = Webhooks(self._request)

    def me(self) -> Any:
        """Return the API key, organization, scopes, quota and usage."""
        return self._request("GET", "/me")

    def platform_rules(self) -> Any:
        """Return composer rules (limits, media, features) keyed by platform."""
        return self._request("GET", "/platform-rules")

    def _sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json: Optional[Any] = None,
    ) -> Any:
        kwargs = _base.build_request_kwargs(params, json)
        url = self.base_url + path
        attempt = 0
        while True:
            response: Optional[httpx.Response] = None
            error: Optional[Exception] = None
            try:
                response = self._client.request(
                    method, url, headers=self._headers, timeout=self.timeout, **kwargs
                )
            except httpx.TransportError as exc:
                error = exc
            if attempt < self.max_retries and _base.should_retry(method, response, error):
                self._sleep(_base.retry_delay(attempt, response))
                attempt += 1
                continue
            if error is not None:
                raise APIConnectionError(f"Request failed: {error}") from error
            assert response is not None
            return _base.process_response(response)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "PostEverywhere":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncPostEverywhere:
    """Async client for the PostEverywhere v1 API. Same arguments as ``PostEverywhere``."""

    accounts: Accounts[Awaitable[Any]]
    posts: Posts[Awaitable[Any]]
    media: Media[Awaitable[Any]]
    ai: AI[Awaitable[Any]]
    analytics: Analytics[Awaitable[Any]]
    campaigns: Campaigns[Awaitable[Any]]
    webhooks: Webhooks[Awaitable[Any]]

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = _base.DEFAULT_TIMEOUT,
        max_retries: int = _base.DEFAULT_MAX_RETRIES,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.api_key = _base.resolve_api_key(api_key)
        self.base_url = _base.resolve_base_url(base_url)
        self.timeout = timeout
        self.max_retries = max_retries
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=timeout)
        self._headers = _base.default_headers(self.api_key)

        self.accounts = Accounts(self._request)
        self.posts = Posts(self._request)
        self.media = Media(self._request)
        self.ai = AI(self._request)
        self.analytics = Analytics(self._request)
        self.campaigns = Campaigns(self._request)
        self.webhooks = Webhooks(self._request)

    def me(self) -> Awaitable[Any]:
        """Return the API key, organization, scopes, quota and usage."""
        return self._request("GET", "/me")

    def platform_rules(self) -> Awaitable[Any]:
        """Return composer rules (limits, media, features) keyed by platform."""
        return self._request("GET", "/platform-rules")

    async def _sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json: Optional[Any] = None,
    ) -> Any:
        kwargs = _base.build_request_kwargs(params, json)
        url = self.base_url + path
        attempt = 0
        while True:
            response: Optional[httpx.Response] = None
            error: Optional[Exception] = None
            try:
                response = await self._client.request(
                    method, url, headers=self._headers, timeout=self.timeout, **kwargs
                )
            except httpx.TransportError as exc:
                error = exc
            if attempt < self.max_retries and _base.should_retry(method, response, error):
                await self._sleep(_base.retry_delay(attempt, response))
                attempt += 1
                continue
            if error is not None:
                raise APIConnectionError(f"Request failed: {error}") from error
            assert response is not None
            return _base.process_response(response)

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "AsyncPostEverywhere":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
