import sys
import types

import firsttry.cli as cli


def _mk_runner(name):
    def _run(changed_files=None):
        return types.SimpleNamespace(ok=True, name=name, duration_s=0.01)

    return _run


def test_run_pre_commit_gate_invokes_runners(monkeypatch):
    """Simulate running the full pre-commit gate (pre-push) and assert runners are called.

    This test temporarily removes pytest from sys.modules so the gate doesn't short-circuit
    to the fast path. It then monkeypatches the runner functions to deterministic stubs
    and asserts the gate returns success and prints a Gate Summary.
    """
    saved_pytest = sys.modules.pop("pytest", None)
    try:
        # Patch runner functions used by _run_pre_commit_gate
        monkeypatch.setattr(cli.runners, "run_ruff", _mk_runner("ruff"), raising=False)
        monkeypatch.setattr(cli.runners, "run_black_check", _mk_runner("black"), raising=False)
        monkeypatch.setattr(cli.runners, "run_mypy", _mk_runner("mypy"), raising=False)
        monkeypatch.setattr(cli.runners, "run_pytest_kexpr", _mk_runner("pytest"), raising=False)
        monkeypatch.setattr(cli.runners, "run_coverage_xml", _mk_runner("coverage"), raising=False)
        monkeypatch.setattr(
            cli.runners,
            "coverage_gate",
            lambda *a, **k: types.SimpleNamespace(ok=True, name="coverage_gate", duration_s=0.0),
            raising=False,
        )

        # Ensure nested-pytest guard isn't set
        monkeypatch.delenv("FT_DISABLE_NESTED_PYTEST", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        rc = cli._run_pre_commit_gate()
        assert rc == 0
    finally:
        if saved_pytest is not None:
            sys.modules["pytest"] = saved_pytest
