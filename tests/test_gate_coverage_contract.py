from __future__ import annotations

import types


from firsttry import cli


class _R:
    def __init__(self, ok: bool, name: str = "fake"):
        self.ok = ok
        self.name = name
        self.duration_s = 0.0
        self.stdout = ""
        self.stderr = ""
        self.cmd = ()


def test_coverage_gate_blocks_commit(monkeypatch):
    """
    The core promise: if coverage gate fails, the gate orchestration must
    block the commit (exit code != 0). We simulate failing coverage and
    assert the returned exit code indicates blocking behavior.
    """

    # Prepare a runners object where everything but coverage passes
    fake = types.SimpleNamespace(
        run_ruff=lambda *a, **k: _R(True, "ruff"),
        run_black_check=lambda *a, **k: _R(True, "black"),
        run_mypy=lambda *a, **k: _R(True, "mypy"),
        run_pytest_kexpr=lambda *a, **k: _R(True, "pytest"),
        run_coverage_xml=lambda *a, **k: _R(True, "coverage_xml"),
        # coverage gate fails
        coverage_gate=lambda *a, **k: _R(False, "coverage_gate"),
    )

    # Monkeypatch the module-level runners used by _run_gate_via_runners
    monkeypatch.setattr(cli, "runners", fake)

    text, code = cli._run_gate_via_runners("pre-commit")

    assert code == 1, "Gate must block (exit code 1) when coverage_gate fails"
    assert "BLOCKED" in text or "FAIL" in text
