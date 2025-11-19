from __future__ import annotations

import hashlib
import hmac
import time


class StripeSignatureError(Exception):
    pass


class LemonSignatureError(Exception):
    pass


def verify_stripe_signature(
    payload: bytes, sig_header: str | None, secret: str, tolerance: int = 300
) -> None:
    """
    Stripe spec: header 'Stripe-Signature' with 't=timestamp,v1=signature'
    signature = HMAC_SHA256(secret, f"{t}.{payload}")
    """
    if not sig_header or not secret:
        raise StripeSignatureError("missing header or secret")

    parts = dict(kv.split("=", 1) for kv in sig_header.split(",") if "=" in kv)
    try:
        t = int(parts["t"])
        v1 = parts["v1"]
    except Exception as e:
        raise StripeSignatureError("malformed header") from e
    if abs(int(time.time()) - t) > tolerance:
        raise StripeSignatureError("timestamp outside tolerance")

    signed = f"{t}.{payload.decode('utf-8')}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, v1):
        raise StripeSignatureError("invalid signature")


def verify_lemon_signature(payload: bytes, sig_header: str | None, secret: str) -> None:
    """
    Lemon Squeezy: header 'X-Signature' = HMAC_SHA256(secret, payload) hex
    """
    if not sig_header or not secret:
        raise LemonSignatureError("missing header or secret")
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig_header):
        raise LemonSignatureError("invalid signature")
