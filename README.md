# PostEverywhere Python SDK

The official Python client for the [PostEverywhere](https://posteverywhere.ai) API.

Schedule and publish posts to Instagram, TikTok, YouTube, LinkedIn, Facebook, X, Threads, Pinterest, Bluesky, Telegram, Discord and WordPress from Python. The library has one dependency (`httpx`), ships type hints, and has a sync and an async client.

## Install

```bash
pip install posteverywhere
```

Python 3.9 or newer.

## Get an API key

Create a key at [app.posteverywhere.ai/developers](https://app.posteverywhere.ai/developers). Keys start with `pe_live_`. Set it as an environment variable:

```bash
export POSTEVERYWHERE_API_KEY="pe_live_..."
```

The client reads `POSTEVERYWHERE_API_KEY` when you do not pass `api_key`.

## Quick start

```python
from posteverywhere import PostEverywhere

client = PostEverywhere()  # or PostEverywhere(api_key="pe_live_...")

# 1. Find the accounts to post to. Account IDs are integers.
accounts = client.accounts.list()["accounts"]
for account in accounts:
    print(account["id"], account["platform"], account["account_name"])

# 2. Schedule a post. Omit scheduled_for to publish now.
post = client.posts.create(
    content="Our spring update is live.",
    account_ids=[accounts[0]["id"]],
    scheduled_for="2026-10-01T14:30:00Z",
    timezone="America/New_York",  # display only, never changes when it fires
)
print(post["post_id"], post["post_status"])

# 3. Check the result for each platform.
results = client.posts.results(post["post_id"])
for r in results["results"]:
    print(r["platform"], r["status"], r.get("platform_post_url"))
```

`scheduled_for` accepts an ISO 8601 string or a `datetime`. A value with no offset is treated as UTC.

Every method returns the `data` object from the API response as a plain `dict`. Field names match the [API reference](https://developers.posteverywhere.ai) exactly.

## More examples

```python
# Attach an image from a public URL
media = client.media.upload_from_url("https://example.com/launch.png")
client.posts.create(content="Launch day", account_ids=[2280], media_ids=[media["media_id"]])

# Different text per platform
client.posts.create(
    content="Default caption",
    account_ids=[2280, 2291],
    platform_content={"x": {"content": "Shorter caption for X"}},
)

# Save a draft, then schedule it later
draft = client.posts.create(content="Draft for review", account_ids=[2280], draft=True)
client.posts.schedule(draft["post_id"], publish_now=True)

# Filter posts
failed = client.posts.list(status="failed", platform=["instagram", "tiktok"], limit=50)

# Retry failed destinations
client.posts.retry(post["post_id"])                # one post
client.posts.retry_failed(platform="tiktok")      # everything that matches a filter

# Create up to 50 posts in one call
batch = client.posts.bulk_create([
    {"content": "Post one", "account_ids": [2280]},
    {"content": "Post two", "account_ids": [2280], "scheduled_for": "2026-10-02T09:00:00Z"},
])
print(batch["summary"])  # {"total": 2, "succeeded": ..., "failed": ...}

# Check an account before you post
health = client.accounts.health(2280)
if not health["can_post"]:
    print("Reconnect needed:", health["status"])

# AI captions (uses AI credits)
captions = client.ai.generate_caption("Summer sale, 30% off", platform="instagram", count=2)

# Analytics, campaigns, rules, and key info
client.analytics.summary(period="week")
client.campaigns.create("Q4 Launch", color="#3b82f6")
client.platform_rules()
client.me()
```

## Resources

| Resource | Methods |
| --- | --- |
| `client.accounts` | `list`, `get`, `health` |
| `client.posts` | `create`, `list`, `get`, `update`, `delete`, `results`, `retry`, `schedule`, `bulk_create`, `retry_failed` |
| `client.media` | `upload_from_url`, `list`, `get`, `delete` |
| `client.ai` | `generate_caption` |
| `client.analytics` | `summary` |
| `client.campaigns` | `list`, `get`, `create`, `update`, `delete` |
| `client.webhooks` | `list`, `get`, `create`, `update`, `delete`, `test` |
| `client` | `me`, `platform_rules` |

## Async

`AsyncPostEverywhere` has the same methods. Each one returns a coroutine.

```python
import asyncio
from posteverywhere import AsyncPostEverywhere

async def main():
    async with AsyncPostEverywhere() as client:
        accounts = await client.accounts.list()
        post = await client.posts.create(
            content="Hello from asyncio",
            account_ids=[a["id"] for a in accounts["accounts"]],
        )
        print(await client.posts.results(post["post_id"]))

asyncio.run(main())
```

## Errors

Failed requests raise a subclass of `PostEverywhereError`. Each error has `status`, `code`, `message`, `request_id` and `details`.

| Exception | When |
| --- | --- |
| `ValidationError` | 400 or 422, the request was rejected |
| `AuthenticationError` | 401, the key is missing, invalid, revoked or expired |
| `PaymentRequiredError` | 402, no active subscription or not enough AI credits |
| `PermissionDeniedError` | 403, the key lacks the scope, or a quota blocks the call |
| `NotFoundError` | 404 |
| `ConflictError` | 409, for example scheduling a post that is not a draft |
| `RateLimitError` | 429, has `retry_after` in seconds |
| `APIError` | 5xx or any other unexpected status |
| `APIConnectionError` | network error or timeout, no response |

```python
from posteverywhere import PostEverywhere, RateLimitError, ValidationError

client = PostEverywhere()
try:
    client.posts.create(content="Hi", account_ids=[2280], scheduled_for="2020-01-01T00:00:00Z")
except ValidationError as e:
    print(e.code, e.message)  # past_schedule_time ...
except RateLimitError as e:
    print("Try again in", e.retry_after, "seconds")
```

Include `request_id` when you contact support.

## Retries and timeouts

The client retries up to `max_retries` times (default 2):

- 429 responses, after the `Retry-After` delay.
- 5xx responses on `GET` and `DELETE` requests, with exponential backoff.
- Connection errors.

It does not retry a 5xx on `POST` or `PATCH`. The server may have done the work, and a retry could publish a post twice. Check with `posts.list` or `posts.get` first.

```python
client = PostEverywhere(timeout=30.0, max_retries=5)
```

The default timeout is 120 seconds, because AI generation can be slow.

## Webhooks

Each webhook delivery has an `X-PostEverywhere-Signature` header. It is `sha256=` plus the HMAC-SHA256 of the raw body, keyed with the `secret` you got when you created the webhook. Verify it before you trust the payload:

```python
from posteverywhere import verify_webhook_signature

# Flask example
@app.post("/hooks/posteverywhere")
def hook():
    ok = verify_webhook_signature(
        request.get_data(),  # the RAW body, not re-encoded JSON
        request.headers.get("X-PostEverywhere-Signature"),
        WEBHOOK_SECRET,
        timestamp=request.headers.get("X-PostEverywhere-Timestamp"),  # rejects deliveries older than 5 minutes
    )
    if not ok:
        return "invalid signature", 401
    event = request.get_json()
    print(event["event"], event["data"])
    return "", 200
```

Create a webhook and send a test event:

```python
hook = client.webhooks.create(
    "https://example.com/hooks/posteverywhere",
    events=["post.published", "post.failed"],
)
print(hook["secret"])  # shown only once: save it now
client.webhooks.test(hook["id"])
```

## Links

- API reference: [developers.posteverywhere.ai](https://developers.posteverywhere.ai)
- Node.js SDK: [github.com/posteverywhere/sdk](https://github.com/posteverywhere/sdk)
- CLI: [github.com/posteverywhere/cli](https://github.com/posteverywhere/cli)
- MCP server for AI assistants: [github.com/posteverywhere/mcp](https://github.com/posteverywhere/mcp)
- Support: support@posteverywhere.ai

## License

MIT
