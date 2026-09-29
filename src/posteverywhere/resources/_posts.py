from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

from .._base import clean
from ._resource import DateLike, Resource, _T, iso, path_id

__all__ = ["Posts"]


def _post_body(
    *,
    content: Optional[str],
    account_ids: Optional[Sequence[int]],
    scheduled_for: Optional[DateLike],
    timezone: Optional[str],
    media_ids: Optional[Sequence[str]],
    platform_content: Optional[Dict[str, Any]],
    cover_photo: Optional[Dict[str, Any]],
    draft: Optional[bool],
    extra: Dict[str, Any],
) -> Dict[str, Any]:
    body = clean(
        {
            "content": content,
            "account_ids": list(account_ids) if account_ids is not None else None,
            "scheduled_for": iso(scheduled_for),
            "timezone": timezone,
            "media_ids": list(media_ids) if media_ids is not None else None,
            "platform_content": platform_content,
            "cover_photo": cover_photo,
            "draft": draft,
        }
    )
    body.update(extra)
    return body


class Posts(Resource[_T]):
    """Create, schedule, list and inspect posts."""

    def create(
        self,
        *,
        content: Optional[str] = None,
        account_ids: Optional[Sequence[int]] = None,
        scheduled_for: Optional[DateLike] = None,
        timezone: Optional[str] = None,
        media_ids: Optional[Sequence[str]] = None,
        platform_content: Optional[Dict[str, Any]] = None,
        cover_photo: Optional[Dict[str, Any]] = None,
        draft: Optional[bool] = None,
        **extra: Any,
    ) -> _T:
        """Create a post. Omit ``scheduled_for`` to publish now; set ``draft=True`` to save a draft.

        ``timezone`` is display metadata only. It never changes when the post fires.
        """
        body = _post_body(
            content=content,
            account_ids=account_ids,
            scheduled_for=scheduled_for,
            timezone=timezone,
            media_ids=media_ids,
            platform_content=platform_content,
            cover_photo=cover_photo,
            draft=draft,
            extra=extra,
        )
        return self._request("POST", "/posts", json=body)

    def bulk_create(self, posts: Sequence[Dict[str, Any]]) -> _T:
        """Create up to 50 posts in one call. Check ``results`` for each item's outcome.

        Each item uses the same fields as ``create``. Partial failure does not
        raise: the returned ``summary`` and ``results`` say which items failed.
        """
        items = [{k: iso(v) for k, v in p.items() if v is not None} for p in posts]
        return self._request("POST", "/posts/bulk", json={"posts": items})

    def list(
        self,
        *,
        status: Optional[Union[str, Sequence[str]]] = None,
        platform: Optional[Union[str, Sequence[str]]] = None,
        account_id: Optional[int] = None,
        campaign_id: Optional[int] = None,
        created_after: Optional[DateLike] = None,
        created_before: Optional[DateLike] = None,
        scheduled_after: Optional[DateLike] = None,
        scheduled_before: Optional[DateLike] = None,
        published_after: Optional[DateLike] = None,
        published_before: Optional[DateLike] = None,
        updated_after: Optional[DateLike] = None,
        search: Optional[str] = None,
        sort: Optional[str] = None,
        order: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> _T:
        """List posts. ``status`` and ``platform`` accept one value or a list."""
        params = {
            "status": status,
            "platform": platform,
            "account_id": account_id,
            "campaign_id": campaign_id,
            "created_after": iso(created_after),
            "created_before": iso(created_before),
            "scheduled_after": iso(scheduled_after),
            "scheduled_before": iso(scheduled_before),
            "published_after": iso(published_after),
            "published_before": iso(published_before),
            "updated_after": iso(updated_after),
            "search": search,
            "sort": sort,
            "order": order,
            "limit": limit,
            "offset": offset,
        }
        return self._request("GET", "/posts", params=params)

    def get(self, post_id: str) -> _T:
        """Get a post with its per-destination statuses."""
        return self._request("GET", f"/posts/{path_id(post_id)}")

    def update(
        self,
        post_id: str,
        *,
        content: Optional[str] = None,
        scheduled_for: Optional[DateLike] = None,
        timezone: Optional[str] = None,
        account_ids: Optional[Sequence[int]] = None,
        media_ids: Optional[Sequence[str]] = None,
        platform_content: Optional[Dict[str, Any]] = None,
        **extra: Any,
    ) -> _T:
        """Update a scheduled or draft post. Pass at least one field."""
        body = clean(
            {
                "content": content,
                "scheduled_for": iso(scheduled_for),
                "timezone": timezone,
                "account_ids": list(account_ids) if account_ids is not None else None,
                "media_ids": list(media_ids) if media_ids is not None else None,
                "platform_content": platform_content,
            }
        )
        body.update(extra)
        return self._request("PATCH", f"/posts/{path_id(post_id)}", json=body)

    def delete(
        self, post_id: str, *, delete_on_platforms: Optional[Union[str, List[str]]] = None
    ) -> _T:
        """Delete a post. Published copies stay live unless ``delete_on_platforms="x"``."""
        return self._request(
            "DELETE",
            f"/posts/{path_id(post_id)}",
            params={"delete_on_platforms": delete_on_platforms},
        )

    def results(self, post_id: str) -> _T:
        """Get per-platform publish results (status and ``platform_post_url``)."""
        return self._request("GET", f"/posts/{path_id(post_id)}/results")

    def retry(self, post_id: str) -> _T:
        """Queue every failed destination of one post for another attempt."""
        return self._request("POST", f"/posts/{path_id(post_id)}/retry")

    def schedule(
        self,
        post_id: str,
        *,
        scheduled_for: Optional[DateLike] = None,
        publish_now: Optional[bool] = None,
        account_ids: Optional[Sequence[int]] = None,
        timezone: Optional[str] = None,
    ) -> _T:
        """Turn a draft into a live post. Pass ``scheduled_for`` or ``publish_now=True``."""
        body = clean(
            {
                "scheduled_for": iso(scheduled_for),
                "publish_now": publish_now,
                "account_ids": list(account_ids) if account_ids is not None else None,
                "timezone": timezone,
            }
        )
        return self._request("POST", f"/posts/{path_id(post_id)}/schedule", json=body)

    def retry_failed(
        self,
        *,
        post_ids: Optional[Sequence[str]] = None,
        account_id: Optional[int] = None,
        platform: Optional[str] = None,
        failed_after: Optional[DateLike] = None,
        failed_before: Optional[DateLike] = None,
        max_attempts: Optional[int] = None,
    ) -> _T:
        """Retry every failed destination that matches a filter. Pass at least one filter."""
        body = clean(
            {
                "post_ids": list(post_ids) if post_ids is not None else None,
                "account_id": account_id,
                "platform": platform,
                "failed_after": iso(failed_after),
                "failed_before": iso(failed_before),
                "max_attempts": max_attempts,
            }
        )
        return self._request("POST", "/posts/retry-failed", json=body)
