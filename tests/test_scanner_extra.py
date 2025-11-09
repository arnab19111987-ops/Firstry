import json

import firsttry.scanner as scanner


def test_collect_type_section_monkeypatched(monkeypatch):
    # Simulate mypy JSON output with one error
    payload = [
        {
            "filename": "src/foo.py",
            "line": 10,
            "severity": "error",
            "code": "attr",
            "message": "bad thing",
        }
    ]

    monkeypatch.setattr(scanner, "_run_cmd", lambda cmd: (0, json.dumps(payload), ""))
    issues, summary = scanner._collect_type_section()
    assert isinstance(issues, list)
    assert len(issues) == 1
    assert summary.manual_count == 1


def test_collect_security_section_with_baseline(tmp_path, monkeypatch):
    # Create a fake bandit JSON output with a HIGH finding
    bandit = {
        "results": [
            {
                "filename": str(tmp_path / "src" / "vuln.py"),
                "issue_severity": "HIGH",
                "issue_text": "use of eval",
                "line_number": 5,
            }
        ]
    }

    # Put a baseline file that baselines nothing (empty files: list)
    baseline = tmp_path / "firsttry_security_baseline.yml"
    baseline.write_text("files:\n  - 'some/other/file.py'\n")

    # Ensure working dir is tmp_path for the duration of this call
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(scanner, "_run_cmd", lambda cmd: (0, json.dumps(bandit), ""))

    (
        issues,
        summary,
        has_high,
        high_unreviewed,
        baselined,
        high_unreviewed_files,
        baselined_files,
    ) = scanner._collect_security_section()
    assert isinstance(issues, list)
    assert has_high is True
    # since baseline doesn't match the file, it should be counted as unreviewed high
    assert high_unreviewed >= 1


def test_scan_with_ruff_handles_bad_json(monkeypatch):
    # Simulate ruff producing invalid JSON (should be handled gracefully)
    monkeypatch.setattr(scanner, "_run_cmd", lambda cmd: (0, "not-a-json", ""))
    issues = scanner._scan_with_ruff()
    assert isinstance(issues, list)
    # invalid json should result in empty issues rather than exception
    assert issues == []
