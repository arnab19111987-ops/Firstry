import pytest
import os

from firsttry import tier


def test_free_cannot_use_pro(monkeypatch):
    # Force the wrapper to report a free tier
    monkeypatch.setattr("firsttry.tier.get_current_tier", lambda: "free")

    @tier.require_tier("pro")
    def pro_only():
        return "ok"

    with pytest.raises(SystemExit) as exc:
        pro_only()
    assert exc.value.code == 2


def test_pro_allowed_and_enterprise_blocked(monkeypatch):
    # Force the wrapper to report a pro tier
    monkeypatch.setattr("firsttry.tier.get_current_tier", lambda: "pro")

    @tier.require_tier("pro")
    def pro_ok():
        return "ok"

    assert pro_ok() == "ok"

    @tier.require_tier("enterprise")
    def ent_only():
        return "ok"

    with pytest.raises(SystemExit) as exc2:
        ent_only()
    assert exc2.value.code == 2


def test_enterprise_allowed(monkeypatch):
    # Force the wrapper to report an enterprise tier
    monkeypatch.setattr("firsttry.tier.get_current_tier", lambda: "enterprise")

    @tier.require_tier("enterprise")
    def ent_ok():
        return "ok"

    assert ent_ok() == "ok"


def test_tier_allowed_func():
    assert tier.tier_allowed("free", "free")
    assert tier.tier_allowed("pro", "free")
    assert tier.tier_allowed("enterprise", "pro")
    assert not tier.tier_allowed("free", "pro")
