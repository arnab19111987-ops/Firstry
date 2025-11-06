from firsttry import gates


def make_pass(name: str):
    return gates.GateResult(
        name=name,
        status="PASS",
        info="ok",
        details="fine",
        returncode=0,
    )


def make_fail(name: str):
    return gates.GateResult(
        name=name,
        status="FAIL",
        info="bad",
        details="failed",
        returncode=1,
    )


def test_run_gate_all_pass(monkeypatch):
    # Monkeypatch the check functions used by the gate
    monkeypatch.setattr(gates, "check_lint", lambda: make_pass("Lint"))
    monkeypatch.setattr(gates, "check_types", lambda: make_pass("Types"))
    monkeypatch.setattr(gates, "check_tests", lambda: make_pass("Tests"))
    monkeypatch.setattr(gates, "check_sqlite_drift", lambda: make_pass("SQLite Drift"))
    monkeypatch.setattr(gates, "check_ci_mirror", lambda: make_pass("CI Mirror"))

    results, ok = gates.run_gate("pre-commit")

    assert ok is True
    assert all(r.get("ok") is True for r in results)


def test_run_gate_reports_fail(monkeypatch):
    # Make one of the checks fail
    monkeypatch.setattr(gates, "check_lint", lambda: make_pass("Lint"))
    monkeypatch.setattr(gates, "check_types", lambda: make_pass("Types"))
    monkeypatch.setattr(gates, "check_tests", lambda: make_fail("Tests"))
    monkeypatch.setattr(gates, "check_sqlite_drift", lambda: make_pass("SQLite Drift"))
    monkeypatch.setattr(gates, "check_ci_mirror", lambda: make_pass("CI Mirror"))

    results, ok = gates.run_gate("pre-commit")

    assert ok is False
    # Ensure at least one result has ok == False and status == 'FAIL'
    assert any((not r.get("ok")) and r.get("status") == "FAIL" for r in results)


def test_format_summary_messages():
    r1 = make_pass("Lint")
    r2 = make_fail("Tests")
    s_ok = gates.format_summary("pre-commit", [r1, r2], overall_ok=False)
    assert "Verdict: BLOCKED" in s_ok or "BLOCKED" in s_ok
