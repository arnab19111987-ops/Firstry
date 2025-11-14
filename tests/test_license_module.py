import pytest
import os

from firsttry import license as ft_license


def test_free_cannot_use_pro(monkeypatch):
    monkeypatch.delenv("FIRSTTRY_FORCE_TIER", raising=False)
    monkeypatch.setenv("FIRSTTRY_TIER", "free-lite")

    @ft_license.require_tier("pro")
    def pro_only():
        return "ok"

    with pytest.raises(SystemExit) as exc:
        pro_only()
    assert exc.value.code == 2


def test_pro_can_use_pro(monkeypatch):
    monkeypatch.setenv("FIRSTTRY_TIER", "pro")

    @ft_license.require_tier("pro")
    def pro_only():
        return "ok"

    assert pro_only() == "ok"


def test_pro_cannot_use_enterprise(monkeypatch):
    monkeypatch.setenv("FIRSTTRY_TIER", "pro")

    @ft_license.require_tier("enterprise")
    def ent_only():
        return "ok"

    with pytest.raises(SystemExit) as exc:
        ent_only()
    assert exc.value.code == 2
