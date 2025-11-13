from firsttry.gates import run_pre_commit_gate
from firsttry.gates import run_pre_push_gate


def test_run_pre_commit_gate_contains_core_checks():
    cmds = run_pre_commit_gate()
    joined = "\n".join(cmds)
    assert "ruff check" in joined
    assert "mypy" in joined
    assert "pytest" in joined
    assert "run_sqlite_probe" in joined


def test_run_pre_push_gate_extends_pre_commit():
    cmds_push = run_pre_push_gate()
    joined = "\n".join(cmds_push)

    # includes pre-commit checks
    assert "ruff check" in joined
    assert "pytest" in joined

    # includes sqlite probe
    assert "run_sqlite_probe" in joined

    # includes security scans
    assert "bandit" in joined

    # includes code complexity
    assert "radon" in joined
