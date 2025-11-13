from importlib import reload

import firsttry.run_swarm as rs


def test_free_uses_local(monkeypatch):
    monkeypatch.delenv("FIRSTTRY_DEMO_MODE", raising=False)
    monkeypatch.delenv("FIRSTTRY_LICENSE_KEY", raising=False)
    reload(rs)
    names = [type(c).__name__ for c in rs.get_caches_for_run()]
    assert names == ["LocalCache"]


def test_pro_adds_s3_when_configured(monkeypatch):
    monkeypatch.setenv("FIRSTTRY_DEMO_MODE", "1")  # force pro
    monkeypatch.setenv("FT_S3_BUCKET", "demo-bucket")
    reload(rs)
    names = [type(c).__name__ for c in rs.get_caches_for_run()]
    assert names[0] == "S3Cache"
    assert "LocalCache" in names
