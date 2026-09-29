import asyncio
import json
from datetime import datetime, timezone

import httpx
import pytest

import posteverywhere
from posteverywhere import (
    APIConnectionError,
    APIError,
    AsyncPostEverywhere,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PaymentRequiredError,
    PermissionDeniedError,
    PostEverywhere,
    PostEverywhereError,
    RateLimitError,
    ValidationError,
)

BASE = "https://app.posteverywhere.ai/api/v1"
META = {"request_id": "1a2b3c4d", "timestamp": "2026-07-08T09:00:00.000Z"}


def ok(data, status=200):
    return httpx.Response(status, json={"data": data, "error": None, "meta": META})


def err(status, code, message="nope", headers=None, details=None):
    body = {
        "data": None,
        "error": {"message": message, "code": code, "details": details},
        "meta": META,
    }
    return httpx.Response(status, json=body, headers=headers)


class Recorder:
    """A MockTransport handler that replays responses and records requests."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def make_client(handler, **kwargs):
    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = PostEverywhere("pe_live_test", http_client=http, **kwargs)
    client.sleeps = []
    client._sleep = client.sleeps.append  # no real waiting in tests
    return client


def test_unwraps_envelope_and_sends_auth():
    rec = Recorder(ok({"accounts": [{"id": 2280, "platform": "instagram"}]}))
    client = make_client(rec)
    data = client.accounts.list()
    assert data == {"accounts": [{"id": 2280, "platform": "instagram"}]}
    req = rec.requests[0]
    assert str(req.url) == f"{BASE}/accounts"
    assert req.headers["Authorization"] == "Bearer pe_live_test"
    assert req.headers["User-Agent"].startswith("posteverywhere-python/")


def test_api_key_from_env(monkeypatch):
    monkeypatch.setenv("POSTEVERYWHERE_API_KEY", "pe_live_env")
    client = PostEverywhere()
    assert client.api_key == "pe_live_env"
    client.close()


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("POSTEVERYWHERE_API_KEY", raising=False)
    with pytest.raises(PostEverywhereError, match="POSTEVERYWHERE_API_KEY"):
        PostEverywhere()


def test_create_post_request_body():
    rec = Recorder(ok({"post_id": "p1", "destinations": []}, status=201))
    client = make_client(rec)
    data = client.posts.create(
        content="Big news",
        account_ids=[2280, 2291],
        scheduled_for=datetime(2026, 7, 10, 14, 30, tzinfo=timezone.utc),
        timezone="America/New_York",
        media_ids=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
        platform_content={"x": {"content": "Short version"}},
    )
    assert data["post_id"] == "p1"
    req = rec.requests[0]
    assert req.method == "POST"
    assert str(req.url) == f"{BASE}/posts"
    assert req.headers["Content-Type"] == "application/json"
    assert json.loads(req.content) == {
        "content": "Big news",
        "account_ids": [2280, 2291],
        "scheduled_for": "2026-07-10T14:30:00+00:00",
        "timezone": "America/New_York",
        "media_ids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
        "platform_content": {"x": {"content": "Short version"}},
    }


def test_list_posts_query_params():
    rec = Recorder(ok({"posts": [], "pagination": {"limit": 20, "offset": 0}}))
    client = make_client(rec)
    client.posts.list(status=["scheduled", "publishing"], platform="instagram", limit=20)
    params = rec.requests[0].url.params
    assert params["status"] == "scheduled,publishing"
    assert params["platform"] == "instagram"
    assert params["limit"] == "20"
    assert "offset" not in params


def test_other_paths():
    rec = Recorder(*[ok({}) for _ in range(6)])
    client = make_client(rec)
    client.me()
    client.platform_rules()
    client.posts.results("abc")
    client.media.delete("m1", force=True)
    client.analytics.summary(period="custom", from_="2026-07-01T00:00:00Z", to="2026-07-31T00:00:00Z")
    client.webhooks.test("w1")
    urls = [str(r.url) for r in rec.requests]
    assert urls[0] == f"{BASE}/me"
    assert urls[1] == f"{BASE}/platform-rules"
    assert urls[2] == f"{BASE}/posts/abc/results"
    assert urls[3] == f"{BASE}/media/m1?force=true"
    assert rec.requests[4].url.params["from"] == "2026-07-01T00:00:00Z"
    assert rec.requests[5].method == "POST" and urls[5] == f"{BASE}/webhooks/w1/test"


def test_bulk_partial_failure_returns_data():
    data = {"summary": {"total": 2, "succeeded": 1, "failed": 1}, "results": []}
    rec = Recorder(ok(data, status=207))
    client = make_client(rec)
    assert client.posts.bulk_create([{"content": "a", "account_ids": [1]}]) == data
    assert json.loads(rec.requests[0].content) == {"posts": [{"content": "a", "account_ids": [1]}]}


@pytest.mark.parametrize(
    "status,cls",
    [
        (400, ValidationError),
        (401, AuthenticationError),
        (402, PaymentRequiredError),
        (403, PermissionDeniedError),
        (404, NotFoundError),
        (409, ConflictError),
        (422, ValidationError),
        (500, APIError),
    ],
)
def test_error_mapping(status, cls):
    rec = Recorder(err(status, "some_code", "Something failed", details={"field": "x"}))
    client = make_client(rec, max_retries=0)
    with pytest.raises(cls) as info:
        client.posts.get("p1")
    e = info.value
    assert e.status == status
    assert e.code == "some_code"
    assert e.message == "Something failed"
    assert e.request_id == "1a2b3c4d"
    assert e.details == {"field": "x"}
    assert isinstance(e, PostEverywhereError)


def test_non_json_error_body():
    rec = Recorder(httpx.Response(502, text="<html>Bad gateway</html>"))
    client = make_client(rec, max_retries=0)
    with pytest.raises(APIError) as info:
        client.accounts.list()
    assert info.value.status == 502


def test_rate_limit_retries_and_respects_retry_after():
    rec = Recorder(err(429, "rate_limit_exceeded", headers={"Retry-After": "7"}), ok({"ok": True}))
    client = make_client(rec)
    assert client.posts.create(content="hi", account_ids=[1]) == {"ok": True}
    assert len(rec.requests) == 2
    assert client.sleeps == [7.0]


def test_rate_limit_error_after_retries_exhausted():
    responses = [err(429, "rate_limit_exceeded", headers={"Retry-After": "3"}) for _ in range(3)]
    rec = Recorder(*responses)
    client = make_client(rec, max_retries=2)
    with pytest.raises(RateLimitError) as info:
        client.accounts.list()
    assert info.value.retry_after == 3.0
    assert len(rec.requests) == 3


def test_server_error_retried_on_get():
    rec = Recorder(err(503, "service_unavailable"), ok({"accounts": []}))
    client = make_client(rec)
    assert client.accounts.list() == {"accounts": []}
    assert len(rec.requests) == 2
    assert len(client.sleeps) == 1


def test_server_error_not_retried_on_post():
    # A 5xx on POST may have created the post; retrying could publish twice.
    rec = Recorder(err(500, "internal_error"), ok({}))
    client = make_client(rec)
    with pytest.raises(APIError):
        client.posts.create(content="hi", account_ids=[1])
    assert len(rec.requests) == 1


def test_connection_error_retried_then_raised():
    boom = httpx.ConnectError("refused")
    rec = Recorder(boom, boom, boom)
    client = make_client(rec, max_retries=2)
    with pytest.raises(APIConnectionError):
        client.accounts.list()
    assert len(rec.requests) == 3


def test_no_retry_on_client_error():
    rec = Recorder(err(400, "validation_error"), ok({}))
    client = make_client(rec)
    with pytest.raises(ValidationError):
        client.posts.create(content="", account_ids=[])
    assert len(rec.requests) == 1


def test_async_client():
    rec = Recorder(err(429, "rate_limit_exceeded", headers={"Retry-After": "1"}), ok({"post_id": "p9"}))

    async def run():
        http = httpx.AsyncClient(transport=httpx.MockTransport(rec))
        sleeps = []

        async def fake_sleep(seconds):
            sleeps.append(seconds)

        async with AsyncPostEverywhere("pe_live_test", http_client=http) as client:
            client._sleep = fake_sleep
            data = await client.posts.create(content="hi", account_ids=[1])
        await http.aclose()
        return data, sleeps

    data, sleeps = asyncio.run(run())
    assert data == {"post_id": "p9"}
    assert sleeps == [1.0]
    assert json.loads(rec.requests[1].content) == {"content": "hi", "account_ids": [1]}


def test_async_error_mapping():
    rec = Recorder(err(404, "not_found"))

    async def run():
        http = httpx.AsyncClient(transport=httpx.MockTransport(rec))
        client = AsyncPostEverywhere("pe_live_test", http_client=http)
        try:
            await client.accounts.get(1)
        finally:
            await http.aclose()

    with pytest.raises(NotFoundError):
        asyncio.run(run())


def test_version():
    assert posteverywhere.__version__ == "0.1.0"
