import firsttry.cli as c


def test_positional_tier_delegates(monkeypatch):
    called = {}

    def fake_run(repo_root, plan, use_remote_cache, workers, **kwargs):
        called["tier"] = "free-lite"
        return {}

    monkeypatch.setattr(c, "run_plan", fake_run)
    # Call cmd_run directly with a positional tier
    res = c.cmd_run(["free-lite"])
    assert res == 0
    assert called.get("tier") == "free-lite"


def test_flag_tier_delegates(monkeypatch):
    called = {}

    def fake_run(repo_root, plan, use_remote_cache, workers, **kwargs):
        called["tier"] = "lite"
        return {}

    monkeypatch.setattr(c, "run_plan", fake_run)
    res = c.cmd_run(["--tier", "lite"])
    assert res == 0
    assert called.get("tier") == "lite"
