from firsttry.cache.s3 import s3_enabled


def test_default_off(monkeypatch):
    monkeypatch.delenv("FIRSTTRY_REMOTE_CACHE", raising=False)
    assert s3_enabled() is False
