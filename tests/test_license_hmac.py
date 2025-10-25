import json
from firsttry.license import (
    build_license_payload,
    verify_sig,
    DEFAULT_SHARED_SECRET,
)


def test_license_payload_is_signed_and_verifies():
    payload = build_license_payload(
        valid=True,
        plan="pro",
        expiry="2026-10-24T00:00:00Z",
        secret=DEFAULT_SHARED_SECRET,
    )

    # sanity structure
    assert payload["valid"] is True
    assert payload["plan"] == "pro"
    assert "sig" in payload

    # signature passes check
    assert verify_sig(payload, secret=DEFAULT_SHARED_SECRET) is True

    # tamper and confirm failure
    hacked = dict(payload)
    hacked["plan"] = "free"
    assert verify_sig(hacked, secret=DEFAULT_SHARED_SECRET) is False

    # must also be valid JSON string for CLI --json usage
    dumped = json.dumps(payload)
    assert '"sig":' in dumped
