"""
Smoke tests for ft CLI entrypoints and tier gating.

Goal:
- Commands 'local', 'ci-parity', 'pytest', 'mypy' exist and parse.
- Pro/Enterprise-only commands respect gating (doctor, roi, cache-push, audit, policy, license).
- No real ruff/mypy/pytest/remote calls – everything mocked.
"""

from argparse import Namespace
from typing import Any
from unittest import mock

import pytest
from click.testing import CliRunner

from firsttry import ft as ft_mod
from firsttry import license_guard
from firsttry import tier as tier_mod


def _pre_commit_fast_gate(ns: Namespace) -> int:
    # simple stub: always "succeeds"
    return 0


def _cmd_mirror_ci(ns: Namespace) -> int:
    # simple stub: always "succeeds"
    return 0


def _cmd_ci(ns: Namespace) -> int:
    # simple stub: always "succeeds"
    return 0


@pytest.mark.parametrize("cmd", ["local", "ci-parity", "pytest", "mypy"])
def test_core_commands_parse_and_call_handler(cmd, monkeypatch):
    """
    Ensure the thin `ft` CLI entrypoints exist and run their handlers.
    We stub underlying heavy handlers to avoid real work.
    """

    runner = CliRunner()

    # Stub heavy internals referenced by ft commands
    monkeypatch.setattr(ft_mod, "_cli", mock.MagicMock(), raising=False)

    # Provide lightweight implementations used by the shim
    def _pre_commit_fast_gate() -> int:
        return 0

    def _cmd_mirror_ci(ns: Any) -> int:
        return 0

    def _cmd_ci(ns: Any) -> int:
        return 0

    ft_mod._cli.pre_commit_fast_gate = _pre_commit_fast_gate
    ft_mod._cli.cmd_mirror_ci = _cmd_mirror_ci
    ft_mod._cli.cmd_ci = _cmd_ci

    result = runner.invoke(ft_mod.main, [cmd])
    # Click wraps SystemExit — ensure process returned with an int exit code
    assert result.exit_code == 0


@pytest.mark.parametrize(
    "current_tier,cmd,requires",
    [
        ("free-lite", "doctor", "pro"),
        ("free-lite", "roi", "pro"),
        ("free-lite", "cache-push", "pro"),
        ("pro", "audit", "enterprise"),
        ("pro", "policy", "enterprise"),
        ("pro", "license", "enterprise"),
    ],
)
def test_pro_and_enterprise_only_commands_are_gated(current_tier, cmd, requires, monkeypatch):
    """
    Pro/Enterprise-only commands should fail cleanly when run from lower tier.
    """

    runner = CliRunner()

    # Patch license resolver used by firsttry.tier
    def _get_current_tier() -> str:
        return current_tier

    monkeypatch.setattr(license_guard, "get_current_tier", _get_current_tier, raising=False)

    # Stub internals so commands don't run real subsystems if invoked
    monkeypatch.setattr(ft_mod, "_cli", mock.MagicMock(), raising=False)
    ft_mod._cli.pre_commit_fast_gate = _pre_commit_fast_gate
    ft_mod._cli.cmd_mirror_ci = _cmd_mirror_ci
    ft_mod._cli.cmd_ci = _cmd_ci

    result = runner.invoke(ft_mod.main, [cmd])
    # Gated commands should exit non-zero for lower tiers
    assert result.exit_code != 0
    out = (result.output or "").lower()
    assert requires in out
    assert tier_mod.get_current_tier().lower() in out
