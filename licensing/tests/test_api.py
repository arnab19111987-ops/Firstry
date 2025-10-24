from fastapi.testclient import TestClient
from app.main import app
import hmac
import hashlib
import time

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_verify_unknown_product():
    r = client.post("/v1/license/verify", json={"product": "other", "key": "ABC"})
    assert r.status_code == 200
    js = r.json()
    assert js["valid"] is False
    assert "unknown" in js["reason"]


def test_verify_missing_key(monkeypatch):
    # No FIRSTTRY_KEYS set
    r = client.post("/v1/license/verify", json={"product": "firsttry", "key": "NOPE"})
    assert r.status_code == 200
    assert r.json()["valid"] is False


def test_verify_valid_key(monkeypatch):
    monkeypatch.setenv("FIRSTTRY_KEYS", "ABC123,PRO456:featA|featB")
    # re-import to refresh store
    from importlib import reload
    import app.licensing as lic

    reload(lic)
    from app.main import license_verify  # noqa

    r = client.post("/v1/license/verify", json={"product": "firsttry", "key": "PRO456"})
    assert r.status_code == 200
    js = r.json()
    assert js["valid"] is True
    assert set(js["features"]) == {"featA", "featB"}


def test_webhooks_accept(monkeypatch):
    # Build valid Stripe signature
    payload = b"{}"
    stripe_secret = "whsec_test"
    t = int(time.time())
    signed = f"{t}.{payload.decode()}".encode()
    sig = hmac.new(stripe_secret.encode(), signed, hashlib.sha256).hexdigest()
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", stripe_secret)
    r1 = client.post(
        "/v1/webhook/stripe",
        data=payload,
        headers={"Stripe-Signature": f"t={t},v1={sig}"},
    )

    # Build valid Lemon Squeezy signature
    lemon_secret = "lem_secret"
    lemon_sig = hmac.new(lemon_secret.encode(), payload, hashlib.sha256).hexdigest()
    monkeypatch.setenv("LEMON_SQUEEZY_WEBHOOK_SECRET", lemon_secret)
    r2 = client.post(
        "/v1/webhook/lemonsqueezy", data=payload, headers={"X-Signature": lemon_sig}
    )

    assert r1.status_code == 200 and r2.status_code == 200
