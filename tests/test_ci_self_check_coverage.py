import json
from pathlib import Path

import pytest

from tools.ci_self_check import CISelfCheck


def make_cov_json(path: Path, files):
    payload = {"files": {f: {} for f in files}}
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_check_critical_coverage_json_pass(tmp_path):
    """All critical files present in coverage.json -> no SystemExit."""
    cov = tmp_path / "coverage.json"
    files = [
        "src/firsttry/state.py",
        "src/firsttry/planner.py",
        "src/firsttry/scanner.py",
        "src/firsttry/smart_pytest.py",
    ]
    make_cov_json(cov, files)

    checker = CISelfCheck(workspace_root=str(tmp_path))

    # Should not raise
    assert checker.check_critical_coverage() is True


def test_check_critical_coverage_json_fail(tmp_path):
    """Missing a critical file should raise SystemExit."""
    cov = tmp_path / "coverage.json"
    files = [
        "src/firsttry/state.py",
        "src/firsttry/planner.py",
        "src/firsttry/scanner.py",
        # smart_pytest.py is intentionally missing
    ]
    make_cov_json(cov, files)

    checker = CISelfCheck(workspace_root=str(tmp_path))

    with pytest.raises(SystemExit):
        checker.check_critical_coverage()
