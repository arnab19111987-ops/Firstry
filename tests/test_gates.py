from firsttry.gates import run_pre_commit_gate, run_pre_push_gate


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

    # includes docker smoke
    assert "run_docker_smoke" in joined

    # includes pg drift
    assert "run_pg_probe" in joined

    # includes hadolint / actionlint
    assert "hadolint" in joined
    assert "actionlint" in joined
