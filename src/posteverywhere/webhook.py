"""Verify the signature on webhook deliveries from PostEverywhere.

Each delivery carries ``X-PostEverywhere-Signature: sha256=<hex>``, the
HMAC-SHA256 of the raw request body keyed with your webhook ``secret``, and
``X-PostEverywhere-Timestamp`` (unix seconds).
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Optional, Union

__all__ = ["verify_webhook_signature", "SIGNATURE_HEADER", "TIMESTAMP_HEADER"]

SIGNATURE_HEADER = "X-PostEverywhere-Signature"
TIMESTAMP_HEADER = "X-PostEverywhere-Timestamp"


def verify_webhook_signature(
    payload: Union[bytes, str],
    signature: Optional[str],
    secret: str,
    *,
    timestamp: Optional[Union[str, int]] = None,
    tolerance: Optional[int] = 300,
) -> bool:
    """Return True if ``signature`` matches ``payload``.

    Args:
        payload: The RAW request body. Do not parse and re-encode the JSON first.
        signature: The ``X-PostEverywhere-Signature`` header value.
        secret: The ``whsec_...`` secret from webhook creation.
        timestamp: Optional ``X-PostEverywhere-Timestamp`` header value. When
            given, deliveries older or newer than ``tolerance`` seconds fail.
        tolerance: Allowed clock skew in seconds. ``None`` turns the check off.
    """
    if not signature or not signature.startswith("sha256="):
        return False
    body = payload.encode("utf-8") if isinstance(payload, str) else payload
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature[len("sha256=") :], expected):
        return False
    if timestamp is not None and tolerance is not None:
        try:
            sent = int(timestamp)
        except (TypeError, ValueError):
            return False
        if abs(time.time() - sent) > tolerance:
            return False
    return True
