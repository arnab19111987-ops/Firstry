import firsttry.gates as gates


def test_gate_result_to_dict_normalizes():
    gr = gates.GateResult(name="Lint", status="PASS", details="All good")
    d = gates.gate_result_to_dict(gr)
    assert d["ok"] is True
    assert d["returncode"] == 0
    assert "All good" in d["stdout"]


def test_format_summary_ok_and_fail():
    res_ok = [gates.GateResult(name="Lint..........", status="PASS", info="")]
    txt_ok = gates.format_summary("pre-commit", res_ok, overall_ok=True)
    assert "SAFE TO COMMIT" in txt_ok

    res_fail = [gates.GateResult(name="Lint..........", status="FAIL", info="")]
    txt_fail = gates.format_summary("pre-commit", res_fail, overall_ok=False)
    assert "BLOCKED" in txt_fail


def test_check_lint_tool_missing(monkeypatch):
    def boom(*a, **k):
        raise FileNotFoundError("ruff")

    monkeypatch.setattr("subprocess.run", boom)
    res = gates.check_lint()
    assert res.status == "SKIPPED"


def test_check_docker_smoke_skipped(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    res = gates.check_docker_smoke()
    assert res.status == "SKIPPED" and "no Docker" in res.info


def test_run_gate_invalid_name():
    import pytest

    with pytest.raises(ValueError):
        gates.run_gate("unknown")


def test_run_all_gates_aggregates(monkeypatch):
    # Force PASS for all individual checks to assert aggregation
    monkeypatch.setattr(gates, "check_lint", lambda: gates.GateResult("Lint", "PASS"))
    monkeypatch.setattr(gates, "check_types", lambda: gates.GateResult("Types", "PASS"))
    monkeypatch.setattr(gates, "check_tests", lambda: gates.GateResult("Tests", "PASS"))
    monkeypatch.setattr(
        gates, "check_sqlite_drift", lambda: gates.GateResult("SQLite Drift", "PASS")
    )
    monkeypatch.setattr(
        gates, "check_ci_mirror", lambda: gates.GateResult("CI Mirror", "PASS")
    )
    monkeypatch.setattr(
        gates, "check_pg_drift", lambda: gates.GateResult("PG Drift", "PASS")
    )
    monkeypatch.setattr(
        gates, "check_docker_smoke", lambda: gates.GateResult("Docker Smoke", "PASS")
    )

    out = gates.run_all_gates(None)
    # run_all_gates returns a list of GateResult objects, not a dict
    assert isinstance(out, list)
    assert len(out) >= 3
