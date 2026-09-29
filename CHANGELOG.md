# Changelog

## 0.1.0 (2026-09-29)

First release.

- `PostEverywhere` (sync) and `AsyncPostEverywhere` (async) clients built on httpx.
- Resources: `accounts`, `posts`, `media`, `ai`, `analytics`, `campaigns`, `webhooks`, plus `me()` and `platform_rules()`.
- Unwraps the `{data, error, meta}` response envelope.
- Typed exceptions mapped from HTTP status, with `status`, `code`, `message`, `request_id` and `details`.
- Automatic retries for 429 (honours `Retry-After`), for 5xx on GET and DELETE, and for connection errors.
- `verify_webhook_signature()` for the `X-PostEverywhere-Signature` header.
