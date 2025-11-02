import importlib


def test_get_tier_synonyms(monkeypatch):
    lg = importlib.import_module("firsttry.license_guard")

    monkeypatch.setenv("FIRSTTRY_TIER", "free")
    assert lg.get_tier() == "developer"

    monkeypatch.setenv("FIRSTTRY_TIER", "pro")
    assert lg.get_tier() == "teams"

    monkeypatch.setenv("FIRSTTRY_TIER", "org")
    assert lg.get_tier() == "enterprise"
