"""Unit tests for the gates module commands.

These tests are lightweight and only validate the returned command shapes
and presence of expected fragments (they don't execute the commands).
"""

from __future__ import annotations

from firsttry import gates


def test_pre_commit_gate_commands_shape_and_fragments() -> None:
    cmds = gates.run_pre_commit_gate()
    assert isinstance(cmds, list)
    assert cmds, "pre-commit command list should not be empty"
    assert all(isinstance(c, str) for c in cmds)

    # expected tooling
    assert any("ruff" in c for c in cmds), "ruff missing from pre-commit commands"
    assert any("mypy" in c for c in cmds), "mypy missing from pre-commit commands"
    assert any("-m pytest" in c for c in cmds), "pytest invocation missing"

    # sqlite probe should be invoked via python -c
    assert any("db_sqlite" in c or "run_sqlite_probe" in c for c in cmds)


def test_pre_push_gate_contains_heavier_checks() -> None:
    cmds = gates.run_pre_push_gate()
    assert isinstance(cmds, list)
    assert cmds, "pre-push command list should not be empty"
    assert all(isinstance(c, str) for c in cmds)

    joined = " ".join(cmds)

    # security and scanners
    assert "bandit" in joined or "pip-audit" in joined
    assert "hadolint" in joined
    assert "actionlint" in joined

    # docker smoke and pg drift checks should be present (as python -c snippets)
    assert any("docker_smoke" in c or "run_docker_smoke" in c for c in cmds)
    assert any("db_pg" in c or "run_pg_probe" in c for c in cmds)
