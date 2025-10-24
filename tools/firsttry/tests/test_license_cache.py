from datetime import datetime, timezone

from firsttry.license_cache import (
    CachedLicense,
    save_cache,
    load_cache,
    is_fresh,
    assert_license,
)


def test_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("firsttry.license_cache.CACHE_PATH", tmp_path / "license.json")
    now = datetime.now(timezone.utc)
    save_cache(CachedLicense(key="K", valid=True, features=["A"], ts=now))
    c = load_cache()
    assert c and c.key == "K" and c.valid and c.features == ["A"]
    assert is_fresh(c)


def test_assert_license_missing_env(monkeypatch):
    monkeypatch.delenv("FIRSTTRY_LICENSE_KEY", raising=False)
    monkeypatch.delenv("FIRSTTRY_LICENSE_URL", raising=False)
    ok, feats, reason = assert_license()
    assert ok is False and reason.startswith("missing")


def test_assert_license_uses_remote_then_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("firsttry.license_cache.CACHE_PATH", tmp_path / "license.json")
    monkeypatch.setenv("FIRSTTRY_LICENSE_KEY", "ABC123")
    monkeypatch.setenv("FIRSTTRY_LICENSE_URL", "http://localhost:8081")

    # stub remote_verify
    def fake_remote(url, product, key):
        assert url.endswith(":8081")
        assert product == "firsttry" and key == "ABC123"
        return True, ["featX"]

    monkeypatch.setattr("firsttry.license_cache.remote_verify", fake_remote)

    ok1, feats1, src1 = assert_license()
    assert ok1 and feats1 == ["featX"] and src1 == "remote"

    # second call should hit cache
    ok2, feats2, src2 = assert_license()
    assert ok2 and feats2 == ["featX"] and src2 == "cache"
