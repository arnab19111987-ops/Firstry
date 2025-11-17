from firsttry import license as lic_mod
from firsttry.license import DEFAULT_SHARED_SECRET, require_license


def test_require_license_allows_when_valid(monkeypatch):
    valid_payload = lic_mod.build_license_payload(
        valid=True,
        plan="pro",
        expiry="2099-01-01T00:00:00Z",
        secret=DEFAULT_SHARED_SECRET,
    )

    def fake_load_ok():
        return valid_payload

    monkeypatch.setattr(lic_mod, "load_cached_license", fake_load_ok)

    # should NOT raise SystemExit
    lic_data, _ = require_license()
    assert lic_data["valid"] is True
    assert lic_data["plan"] == "pro"
