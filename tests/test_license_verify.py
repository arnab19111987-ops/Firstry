# tests/test_license_verify.py
from firsttry import license as lic_mod


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def fake_post_ok(url, json, timeout):
    assert "license_key" in json
    return FakeResponse(
        {
            "valid": True,
            "plan": "pro",
            "expiry": "2099-01-01T00:00:00Z",
        }
    )


def test_verify_license_with_server_and_cache(tmp_path, monkeypatch):
    # redirect cache path for isolation
    monkeypatch.setattr(lic_mod, "CACHE_PATH", tmp_path / "license.json")

    info = lic_mod.verify_license(
        license_key="ABC-123",
        server_url="http://fake-server/api/v1/license/verify",
        http_post=fake_post_ok,
    )

    assert info.valid is True
    assert info.plan == "pro"
    assert "expiry" in info.raw

    # cache file created
    cached = lic_mod.load_cached_license()
    assert cached is not None
    assert cached.plan == "pro"

    # now simulate offline: no server_url, no http_post
    info2 = lic_mod.verify_license(
        license_key="ABC-123",
        server_url=None,
        http_post=None,
    )
    assert info2.valid is True
    assert info2.plan == "pro"


def test_verify_license_no_key_defaults_to_free(monkeypatch, tmp_path):
    monkeypatch.delenv("FIRSTTRY_LICENSE_KEY", raising=False)
    monkeypatch.setattr(lic_mod, "CACHE_PATH", tmp_path / "license.json")

    info = lic_mod.verify_license(
        license_key=None,
        server_url=None,
        http_post=None,
    )
    assert info.valid is False
    assert info.plan == "free"
