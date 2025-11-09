from firsttry import scanner


def test_scanner_smoke_and_run_all_precommit():
    # _run_cmd should return 127 for a non-existent binary
    code, out, err = scanner._run_cmd(["this-binary-should-not-exist-xyz"])
    assert code == 127

    # scanning helpers should return lists (they gracefully handle missing tools)
    ruff_issues = scanner._scan_with_ruff()
    assert isinstance(ruff_issues, list)
    black_issues = scanner._scan_with_black()
    assert isinstance(black_issues, list)

    # collect lint section (combines ruff+black)
    issues, summary = scanner._collect_lint_section()
    assert hasattr(summary, "name") and summary.name == "Lint / Style"

    # Running a pre-commit dry-run should succeed and return a ScanResult
    res = scanner.run_all_checks_dry_run("pre-commit")
    assert hasattr(res, "coverage_pct")
    assert isinstance(res.coverage_pct, float)
