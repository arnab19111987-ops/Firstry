"""
Unit tests for tier gating and license guard behavior.

Goal:
- Pro/Enterprise gating returns the right allow/deny decision.
- Error messages are stable and clear.
- No network, no real license verification (use in-memory/fake keys).
"""

from unittest import mock

import pytest

from firsttry import license_guard, tier as tier_mod


def test_require_tier_pro_denies_free_with_clear_message(capsys):
    """
    When current tier is 'free', require_tier('pro') must:
    - deny access
    - print a clear message mentioning Pro and current tier
    - use a stable non-zero exit code (2 from tier.require_tier)
    """

    # license_guard.get_current_tier returns values like 'free-lite' / 'pro' / 'promax'
    with mock.patch.object(license_guard, "get_current_tier", return_value="free-lite"):
        with pytest.raises(SystemExit) as exc:
            # use the decorator from tier module
            @tier_mod.require_tier("pro")
            def fn():
                pass

            fn()

    assert exc.value.code == 2

    out = capsys.readouterr().out + capsys.readouterr().err
    out_lower = out.lower()
    assert "pro" in out_lower
    assert "free" in out_lower
    assert "requires" in out_lower or "locked" in out_lower


def test_require_tier_pro_allows_pro_and_enterprise():
    """
    Pro and Enterprise tiers must both pass require_tier('pro') without exit.
    """
    for t in ("pro", "promax"):
        with mock.patch.object(license_guard, "get_current_tier", return_value=t):
            calls = []

            @tier_mod.require_tier("pro")
            def fn():
                calls.append("ok")

            fn()
            assert calls == ["ok"]


def test_require_tier_enterprise_denies_pro_with_clear_message(capsys):
    """
    Pro must not be able to access enterprise-only features.
    """
    with mock.patch.object(license_guard, "get_current_tier", return_value="pro"):
        with pytest.raises(SystemExit) as exc:

            @tier_mod.require_tier("enterprise")
            def fn2():
                pass

            fn2()

    assert exc.value.code == 2
    out = capsys.readouterr().out + capsys.readouterr().err
    out_lower = out.lower()
    assert "enterprise" in out_lower
    assert "pro" in out_lower
