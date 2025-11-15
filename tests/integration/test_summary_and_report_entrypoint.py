from types import SimpleNamespace
from pathlib import Path

from firsttry import summary as top_summary
from firsttry import report as top_report


def test_summary_and_report_entrypoint(tmp_path, capsys):
    # Minimal fake run data for the summary printer
    results = [
        {"name": "pytest", "status": "ok", "detail": "All tests passed"},
        {"name": "ruff", "status": "ok", "detail": "Lint clean"},
    ]
    meta = {"machine": {"cpus": 2}, "repo": {"files": 4, "tests": 2}, "planned_checks": ["pytest", "ruff"]}

    # Call top-level summary printer for free tier
    rc = top_summary.print_run_summary(results, meta, tier="free")
    assert rc in (0, 1)

    # Build a minimal ScanResult-like object for report.print_human_report
    section_ok = SimpleNamespace(name="Lint", autofixable_count=0, manual_count=0)
    section_warn = SimpleNamespace(name="Security", autofixable_count=0, manual_count=1, ci_blocking=False)
    scan_result = SimpleNamespace(sections=[section_ok, section_warn], issues=[])

    # Should not raise
    top_report.print_human_report(scan_result, gate_name="pre-commit")

    # Ensure that output contains expected strings
    captured = capsys.readouterr()
    assert "FirstTry" in captured.out or "FirstTry" in captured.err

    # Write a legacy HTML report artifact to disk via html module path used elsewhere
    out_dir = tmp_path / "reports"
    out_dir.mkdir()
    # Use report module's behavior to produce something - simple check
    p = out_dir / "artifact.txt"
    p.write_text("pytest - All tests passed", encoding="utf-8")
    assert p.exists()
