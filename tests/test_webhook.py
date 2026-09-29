import hashlib
import hmac
import time

from posteverywhere import verify_webhook_signature

SECRET = "whsec_test_secret"
BODY = b'{"event":"post.published","data":{"post_id":"p1"}}'


def sign(body, secret=SECRET):
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_valid_signature():
    assert verify_webhook_signature(BODY, sign(BODY), SECRET)
    assert verify_webhook_signature(BODY.decode(), sign(BODY), SECRET)


def test_wrong_secret_or_body():
    assert not verify_webhook_signature(BODY, sign(BODY, "whsec_other"), SECRET)
    assert not verify_webhook_signature(BODY + b" ", sign(BODY), SECRET)


def test_missing_or_malformed_header():
    assert not verify_webhook_signature(BODY, None, SECRET)
    assert not verify_webhook_signature(BODY, sign(BODY)[7:], SECRET)


def test_timestamp_tolerance():
    now = int(time.time())
    assert verify_webhook_signature(BODY, sign(BODY), SECRET, timestamp=str(now))
    assert not verify_webhook_signature(BODY, sign(BODY), SECRET, timestamp=now - 3600)
    assert verify_webhook_signature(BODY, sign(BODY), SECRET, timestamp=now - 3600, tolerance=None)
    assert not verify_webhook_signature(BODY, sign(BODY), SECRET, timestamp="abc")
