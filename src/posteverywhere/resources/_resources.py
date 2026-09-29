from __future__ import annotations

from typing import Any, Optional, Sequence

from .._base import clean
from ._resource import DateLike, Resource, _T, iso, path_id

__all__ = ["Accounts", "Media", "AI", "Analytics", "Campaigns", "Webhooks"]


class Accounts(Resource[_T]):
    """Connected social accounts. Account IDs are integers."""

    def list(self) -> _T:
        """List every connected account, each with a short health block."""
        return self._request("GET", "/accounts")

    def get(self, account_id: int) -> _T:
        """Get one account."""
        return self._request("GET", f"/accounts/{path_id(account_id)}")

    def health(self, account_id: int) -> _T:
        """Get a health report: ``status``, ``can_post``, ``needs_reconnection`` and more."""
        return self._request("GET", f"/accounts/{path_id(account_id)}/health")


class Media(Resource[_T]):
    """The media library."""

    def upload_from_url(self, url: str, *, filename: Optional[str] = None) -> _T:
        """Import a public image or MP4 URL.

        Images are ready at once. Videos return ``media_status="uploading"``:
        poll ``media.get(media_id)`` until it is ``ready`` before you attach it.
        """
        return self._request(
            "POST", "/media/upload-from-url", json=clean({"url": url, "filename": filename})
        )

    def list(
        self,
        *,
        type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> _T:
        """List media, newest first. ``type`` is ``image``, ``video`` or ``document``."""
        return self._request(
            "GET", "/media", params={"type": type, "limit": limit, "offset": offset}
        )

    def get(self, media_id: str) -> _T:
        """Get one media item, including ``media_status`` and ``url``."""
        return self._request("GET", f"/media/{path_id(media_id)}")

    def delete(self, media_id: str, *, force: Optional[bool] = None) -> _T:
        """Delete a media item. Pass ``force=True`` if scheduled posts use it."""
        return self._request("DELETE", f"/media/{path_id(media_id)}", params={"force": force})


class AI(Resource[_T]):
    """AI caption generation. Uses your organization's AI credits."""

    def generate_caption(
        self,
        topic: str,
        *,
        platform: Optional[str] = None,
        tone: Optional[str] = None,
        length: Optional[str] = None,
        include_hashtags: Optional[bool] = None,
        include_emojis: Optional[bool] = None,
        count: Optional[int] = None,
    ) -> _T:
        """Generate 1 to 5 captions for a topic. Costs 1 credit per caption returned."""
        body = clean(
            {
                "topic": topic,
                "platform": platform,
                "tone": tone,
                "length": length,
                "include_hashtags": include_hashtags,
                "include_emojis": include_emojis,
                "count": count,
            }
        )
        return self._request("POST", "/ai/generate-caption", json=body)


class Analytics(Resource[_T]):
    """Aggregate post counts and engagement metrics."""

    def summary(
        self,
        *,
        period: Optional[str] = None,
        from_: Optional[DateLike] = None,
        to: Optional[DateLike] = None,
    ) -> _T:
        """Get a summary. ``period`` is today, week, month, all or custom (with ``from_`` and ``to``)."""
        params = {"period": period, "from": iso(from_), "to": iso(to)}
        return self._request("GET", "/analytics/summary", params=params)


class Campaigns(Resource[_T]):
    """Named groups of posts. Campaign IDs are integers."""

    def list(
        self,
        *,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> _T:
        """List campaigns. ``status`` is ``active`` or ``archived``."""
        return self._request(
            "GET", "/campaigns", params={"status": status, "limit": limit, "offset": offset}
        )

    def get(self, campaign_id: int) -> _T:
        return self._request("GET", f"/campaigns/{path_id(campaign_id)}")

    def create(
        self,
        name: str,
        *,
        description: Optional[str] = None,
        color: Optional[str] = None,
        status: Optional[str] = None,
    ) -> _T:
        """Create a campaign. ``color`` is a hex string such as ``#3b82f6``."""
        body = clean({"name": name, "description": description, "color": color, "status": status})
        return self._request("POST", "/campaigns", json=body)

    def update(
        self,
        campaign_id: int,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        status: Optional[str] = None,
    ) -> _T:
        """Update a campaign. Pass at least one field."""
        body = clean({"name": name, "description": description, "color": color, "status": status})
        return self._request("PATCH", f"/campaigns/{path_id(campaign_id)}", json=body)

    def delete(self, campaign_id: int) -> _T:
        """Delete a campaign. Its posts stay; their ``campaign_id`` becomes null."""
        return self._request("DELETE", f"/campaigns/{path_id(campaign_id)}")


class Webhooks(Resource[_T]):
    """Webhook subscriptions. Webhook IDs are UUID strings."""

    def list(self) -> _T:
        return self._request("GET", "/webhooks")

    def get(self, webhook_id: str) -> _T:
        """Get one webhook. The signing secret is not included."""
        return self._request("GET", f"/webhooks/{path_id(webhook_id)}")

    def create(
        self,
        url: str,
        events: Sequence[str],
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> _T:
        """Create a webhook. The response ``secret`` is shown only once: save it."""
        body = clean({"url": url, "events": list(events), "name": name, "description": description})
        return self._request("POST", "/webhooks", json=body)

    def update(
        self,
        webhook_id: str,
        *,
        url: Optional[str] = None,
        events: Optional[Sequence[str]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> _T:
        """Update a webhook. Pass at least one field."""
        body = clean(
            {
                "url": url,
                "events": list(events) if events is not None else None,
                "name": name,
                "description": description,
                "is_active": is_active,
            }
        )
        return self._request("PATCH", f"/webhooks/{path_id(webhook_id)}", json=body)

    def delete(self, webhook_id: str) -> _T:
        return self._request("DELETE", f"/webhooks/{path_id(webhook_id)}")

    def test(self, webhook_id: str) -> _T:
        """Send a signed test event. Check ``ok`` in the result for the delivery outcome."""
        return self._request("POST", f"/webhooks/{path_id(webhook_id)}/test")
