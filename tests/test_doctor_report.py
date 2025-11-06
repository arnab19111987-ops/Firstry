# tests/test_doctor_report.py
from firsttry import doctor


class MockRunner(doctor.Runner):
    def __init__(self, table):
        # table: dict[tuple(cmd), (rc, output)]
        self.table = {tuple(k): v for (k, v) in table.items()}

    def run(self, cmd):
        key = tuple(cmd)
        rc, out = self.table.get(key, (0, "OK"))
        return rc, out


def test_gather_checks_builds_report_and_score():
    runner = MockRunner(
        {
            # pytest passes
            ("python", "-m", "pytest", "-q"): (0, "all good"),
            # ruff fails
            ("ruff", "check", "."): (1, "unused import foo\n"),
            # black passes
            ("black", "--check", "."): (0, "would reformat 0 files"),
            # mypy passes
            ("mypy", "."): (0, "Success: no issues found"),
            # coverage-report passes
            ("coverage", "report", "--show-missing"): (0, "Name Stmts Miss Cover"),
        },
    )

    rep = doctor.gather_checks(runner=runner)

    assert rep.total_count == 5
    # 4/5 pass, so 80%
    assert rep.passed_count == 4
    assert round(rep.score_pct) == 80

    # ruff should be the only failing check
    failing = [c for c in rep.checks if not c.passed]
    assert [c.name for c in failing] == ["ruff"]

    # quickfix suggestions should include hint about ruff autofix
    assert any("ruff" in q.lower() for q in rep.quickfixes)


def test_render_report_md_contains_table_and_quickfix():
    runner = MockRunner(
        {
            ("python", "-m", "pytest", "-q"): (0, "ok"),
            ("ruff", "check", "."): (1, "unused import x"),
            ("black", "--check", "."): (0, "clean"),
            ("mypy", "."): (0, "Success"),
            ("coverage", "report", "--show-missing"): (0, "good"),
        },
    )
    rep = doctor.gather_checks(runner=runner)
    md = doctor.render_report_md(rep)

    # minimal sanity checks on markdown structure
    assert "# FirstTry Doctor Report" in md
    assert "| pytest |" in md
    assert "| ruff |" in md
    assert "Quick Fix Suggestions" in md
    assert "firsttry doctor" in md

    # ensure we didn't accidentally spit huge multiline blobs in table row
    for line in md.splitlines():
        if line.startswith("| ruff |"):
            # first line of output only
            assert "unused import x" in line
            assert "\n" not in line
