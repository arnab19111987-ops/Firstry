from importlib import reload

import firsttry.license_guard as lg


def test_demo_mode_forces_pro(monkeypatch):
    monkeypatch.setenv("FIRSTTRY_DEMO_MODE", "1")
    reload(lg)
    assert lg.get_current_tier() == "pro"
