import hmac
import hashlib
import time
import pytest

from app.webhooks import (
    verify_stripe_signature,
    verify_lemon_signature,
    StripeSignatureError,
    LemonSignatureError,
)


essential_payload = b"{}"


def test_stripe_missing_header_or_secret():
    with pytest.raises(StripeSignatureError):
        verify_stripe_signature(essential_payload, None, "secret")
    with pytest.raises(StripeSignatureError):
        verify_stripe_signature(essential_payload, "t=1,v1=dead", "")


def test_stripe_malformed_header():
    with pytest.raises(StripeSignatureError):
        verify_stripe_signature(essential_payload, "t=notanint", "secret")


def test_stripe_timestamp_outside_tolerance():
    payload = b'{"x":1}'
    secret = "whsec_test"
    old_t = int(time.time()) - 999999
    signed = f"{old_t}.{payload.decode()}".encode()
    sig = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    with pytest.raises(StripeSignatureError):
        verify_stripe_signature(payload, f"t={old_t},v1={sig}", secret, tolerance=10)


def test_stripe_invalid_signature():
    with pytest.raises(StripeSignatureError):
        verify_stripe_signature(essential_payload, "t=1,v1=deadbeef", "whsec_test")


def test_lemon_missing_header_or_secret():
    with pytest.raises(LemonSignatureError):
        verify_lemon_signature(essential_payload, None, "secret")
    with pytest.raises(LemonSignatureError):
        verify_lemon_signature(essential_payload, "abcd", "")


def test_lemon_invalid_signature():
    with pytest.raises(LemonSignatureError):
        verify_lemon_signature(essential_payload, "deadbeef", "lem_secret")
