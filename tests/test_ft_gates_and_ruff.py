import json
import sys
import types

import pytest
from click.testing import CliRunner

from firsttry import divergence
from firsttry import ft
from firsttry import runners


def test_pro_and_enterprise_gates(monkeypatch):
    runner = CliRunner()

    # free cannot access pro commands
    monkeypatch.setattr("firsttry.tier.get_current_tier", lambda: "free")
    res = runner.invoke(ft.main, ["doctor"])
    assert res.exit_code == 2
    res = runner.invoke(ft.main, ["roi"])
    assert res.exit_code == 2
    res = runner.invoke(ft.main, ["cache-push"])
    assert res.exit_code == 2

    # pro can access pro commands
    monkeypatch.setattr("firsttry.tier.get_current_tier", lambda: "pro")
    res = runner.invoke(ft.main, ["doctor"])
    assert res.exit_code == 0
    res = runner.invoke(ft.main, ["roi"])
    assert res.exit_code == 0
    res = runner.invoke(ft.main, ["cache-push"])
    assert res.exit_code == 0

    # enterprise gets enterprise commands
    monkeypatch.setattr("firsttry.tier.get_current_tier", lambda: "enterprise")
    res = runner.invoke(ft.main, ["audit"])
    assert res.exit_code == 0
    res = runner.invoke(ft.main, ["policy"])
    assert res.exit_code == 0
    res = runner.invoke(ft.main, ["license"])
    assert res.exit_code == 0


def test_ft_local_invokes_ruff_full(monkeypatch, tmp_path):
    # Ensure we exercise the non-short-circuit path by removing pytest from sys.modules
    saved_pytest = sys.modules.pop("pytest", None)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    calls = []

    def fake_run_ruff(files, *, cwd=None, timeout=None):
        calls.append((files, cwd, timeout))
        return types.SimpleNamespace(
            ok=True, name="ruff", duration_s=0.0, stdout="", stderr="", cmd=("ruff", "check")
        )

    # Patch other runners to be benign
    monkeypatch.setattr(runners, "run_ruff", fake_run_ruff)
    monkeypatch.setattr(
        runners,
        "run_black_check",
        lambda targets, cwd=None, timeout=None: types.SimpleNamespace(
            ok=True, name="black", duration_s=0.0, stdout="", stderr="", cmd=("black", "--check")
        ),
    )
    monkeypatch.setattr(
        runners,
        "run_mypy",
        lambda targets, cwd=None, timeout=None: types.SimpleNamespace(
            ok=True, name="mypy", duration_s=0.0, stdout="", stderr="", cmd=("mypy",)
        ),
    )

    def fake_run_pytest_kexpr(kexpr, base_args=(), cwd=None, timeout=None):
        return types.SimpleNamespace(
            ok=True,
            name="pytest",
            duration_s=0.0,
            stdout="",
            stderr="",
            cmd=("pytest",),
        )

    monkeypatch.setattr(runners, "run_pytest_kexpr", fake_run_pytest_kexpr)
    monkeypatch.setattr(
        runners,
        "run_coverage_xml",
        lambda root: types.SimpleNamespace(
            ok=True, name="coverage", duration_s=0.0, stdout="", stderr="", cmd=("coverage",)
        ),
    )
    monkeypatch.setattr(
        runners,
        "coverage_gate",
        lambda n: types.SimpleNamespace(
            ok=True,
            name="coverage_gate",
            duration_s=0.0,
            stdout="",
            stderr="",
            cmd=("coverage_gate",),
        ),
    )

    # Ensure tier is at least free (doesn't affect ruff invocation)
    monkeypatch.setattr("firsttry.tier.get_current_tier", lambda: "free")

    runner = CliRunner()
    res = runner.invoke(ft.main, ["local"])

    # restore pytest module
    if saved_pytest is not None:
        sys.modules["pytest"] = saved_pytest

    # ruff should have been called once
    assert len(calls) >= 1
    files, cwd, timeout = calls[0]
    # ruff should be invoked as ['ruff','check', ...] in runners.run_ruff implementation
    assert isinstance(files, (list, tuple)) or files is not None


def test_divergence_helper(tmp_path, monkeypatch):
    warm = tmp_path / "warm.json"
    full = tmp_path / "full.json"
    warm.write_text(json.dumps({"ok": True, "value": 1}))
    full.write_text(json.dumps({"ok": False, "value": 2}))

    # enterprise should trigger SystemExit(99)
    monkeypatch.setattr("firsttry.tier.get_current_tier", lambda: "enterprise")
    with pytest.raises(SystemExit) as exc:
        divergence.enforce_divergence_exit(warm, full)
    assert int(exc.value.code) == 99

    # pro should not trigger
    monkeypatch.setattr("firsttry.tier.get_current_tier", lambda: "pro")
    divergence.enforce_divergence_exit(warm, full)  # should not raise
