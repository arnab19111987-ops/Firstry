import hashlib
import hmac
import time

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_stripe_webhook_ok(monkeypatch):
    payload = b'{"type":"invoice.paid"}'
    secret = "whsec_test"
    t = int(time.time())
    signed = f"{t}.{payload.decode()}".encode()
    sig = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", secret)
    r = client.post(
        "/v1/webhook/stripe",
        data=payload,
        headers={"Stripe-Signature": f"t={t},v1={sig}"},
    )
    assert r.status_code == 200


def test_stripe_webhook_bad_sig(monkeypatch):
    payload = b"{}"
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    r = client.post(
        "/v1/webhook/stripe",
        data=payload,
        headers={"Stripe-Signature": "t=1,v1=deadbeef"},
    )
    assert r.status_code == 400


def test_lemon_webhook_ok(monkeypatch):
    payload = b'{"event":"order_created"}'
    secret = "lem_secret"
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    monkeypatch.setenv("LEMON_SQUEEZY_WEBHOOK_SECRET", secret)
    r = client.post(
        "/v1/webhook/lemonsqueezy", data=payload, headers={"X-Signature": sig}
    )
    assert r.status_code == 200


def test_lemon_webhook_bad_sig(monkeypatch):
    payload = b"{}"
    monkeypatch.setenv(
        "LEMONSQUEEZY_WEBHOOK_SECRET", "lem_secret"
    )  # wrong env on purpose
    r = client.post(
        "/v1/webhook/lemonsqueezy", data=payload, headers={"X-Signature": "deadbeef"}
    )
    assert r.status_code == 400
