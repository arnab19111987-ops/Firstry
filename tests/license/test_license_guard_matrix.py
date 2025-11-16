"""License/tier guard matrix tests.

Goal:
- Explicitly test require_tier() behavior for free/pro/enterprise.
- Validate error messages and exit codes without calling real license APIs.
"""

import types
from unittest import mock

import pytest

import firsttry.license_guard as lg
from firsttry import tier as tier_mod


def test_ensure_license_for_current_tier_noop_for_free_tier(monkeypatch):
    """For free tiers, ensure_license_for_current_tier() should be a no-op."""
    monkeypatch.setattr(lg, "get_current_tier", lambda: "free-lite", raising=False)
    monkeypatch.setattr(lg, "get_tier", lambda: "free-lite", raising=False)
    monkeypatch.setattr(lg, "_get_license_key_from_env", lambda: None, raising=False)
    result = lg.ensure_license_for_current_tier()
    assert result is None or result is True


def test_ensure_license_for_current_tier_raises_on_paid_tier_without_license(monkeypatch):
    """Absence of a valid license on paid tiers should trigger a clear failure."""
    monkeypatch.setattr(lg, "get_current_tier", lambda: "pro", raising=False)

    fake_cache = types.SimpleNamespace(get_current_license=lambda: None)
    monkeypatch.setattr(lg, "license_cache", fake_cache, raising=False)

    with pytest.raises(Exception):
        lg.ensure_license_for_current_tier()


def test_ensure_license_for_current_tier_passes_with_valid_license(monkeypatch):
    """Paid tiers with a valid license key should not raise."""
    monkeypatch.setattr(lg, "get_current_tier", lambda: "pro", raising=False)
    monkeypatch.setattr(lg, "_get_license_key_from_env", lambda: "FAKE-KEY", raising=False)
    monkeypatch.setattr(lg, "_validate_license_offline", lambda key, tier: None, raising=False)
    result = lg.ensure_license_for_current_tier()
    assert result is None or result is True


def _run_guarded(fn):
    """Helper: call a decorated function and return (ok, SystemExit or None)."""
    try:
        fn()
    except SystemExit as exc:
        return False, exc
    return True, None


@pytest.mark.parametrize(
    "current_tier,required,allowed",
    [
        ("free-lite", "pro", False),
        ("free-lite", "enterprise", False),
        ("pro", "pro", True),
        ("pro", "enterprise", False),
        ("enterprise", "pro", True),
        ("enterprise", "enterprise", True),
    ],
)
def test_require_tier_matrix(current_tier, required, allowed, capsys):
    """Matrix:
    - free cannot access pro/enterprise.
    - pro can access pro, not enterprise.
    - enterprise can access everything.
    """

    with mock.patch.object(lg, "get_current_tier", return_value=current_tier):

        @tier_mod.require_tier(required)
        def guarded():
            return "ok"

        ok, exc = _run_guarded(guarded)

        if allowed:
            assert ok is True
            assert exc is None
        else:
            assert ok is False
            assert isinstance(exc, SystemExit)
            assert exc.code != 0
            out = (capsys.readouterr().out + capsys.readouterr().err).lower()
            assert required in out
            assert tier_mod.get_current_tier().lower() in out
            assert "requires" in out or "locked" in out
