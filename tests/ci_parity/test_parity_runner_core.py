"""
High-ROI unit tests for src/firsttry/ci_parity/parity_runner.py.

Goal:
- Hit core pure logic (classification, JSON parsing, report writing)
- Avoid slow subprocesses / real CI runs
- No network, no remote cache
"""

import json

from firsttry.ci_parity import parity_runner

# ---------- classify_warm_outcome coverage ----------


def test_classify_warm_outcome_uses_testmon_for_rc_zero():
    """
    rc == 0  → USE_TESTMON
    This should be the happy path when testmon found tests and all passed.
    """
    decision = parity_runner.classify_warm_outcome(
        testmon_rc=0,
        flaky_nodeids=None,
    )
    name = getattr(decision, "name", str(decision)).upper()
    assert "USE_TESTMON" in name


def test_classify_warm_outcome_no_tests_for_rc_five():
    """
    rc == 5 → NO_TESTS_COLLECTED (or equivalent branch).
    """
    decision = parity_runner.classify_warm_outcome(
        testmon_rc=5,
        flaky_nodeids=None,
    )
    name = getattr(decision, "name", str(decision)).upper()
    assert "SMOKE" in name or "NO_TEST" in name or "FLAKY" in name


def test_classify_warm_outcome_failure_for_other_rc():
    """
    Any other non-zero rc → warm-path failure.
    """
    decision = parity_runner.classify_warm_outcome(
        testmon_rc=1,
        flaky_nodeids=[],
    )
    name = getattr(decision, "name", str(decision)).upper()
    assert "FAIL" in name or "ERROR" in name


# ---------- JSON failure collection helpers ----------


def test_collect_failures_from_valid_json(tmp_path):
    """
    Given a valid pytest-json-report style file, the collector should
    return at least those failing nodeids and not crash.
    """
    report = {
        "tests": [
            {"nodeid": "tests/test_a.py::test_ok", "outcome": "passed"},
            {"nodeid": "tests/test_b.py::test_fail", "outcome": "failed"},
        ]
    }
    json_path = tmp_path / "report.json"
    json_path.write_text(json.dumps(report))

    failures = parity_runner._collect_failures_from_json(json_path)

    # parity_runner returns list[dict], each with nodeid
    nodeids = [d.get("nodeid") for d in failures]
    assert "tests/test_b.py::test_fail" in nodeids
    assert "tests/test_a.py::test_ok" not in nodeids


def test_collect_failures_from_missing_file_returns_empty(tmp_path):
    """
    Missing JSON file should not raise; should return an empty list.
    """
    missing = tmp_path / "no_such_file.json"

    failures = parity_runner._collect_failures_from_json(missing)

    assert failures == []


def test_collect_failures_from_malformed_json_returns_empty(tmp_path):
    """
    Malformed JSON should be handled defensively and result in empty failures.
    """
    bad = tmp_path / "bad.json"
    bad.write_text("{this is not valid json")

    failures = parity_runner._collect_failures_from_json(bad)

    assert failures == []


# ---------- report writing helpers ----------


def test_write_self_check_report_creates_json(tmp_path, monkeypatch):
    """
    Exercise the report writer with a tiny in-memory self-check result.
    """
    out_dir = tmp_path / "artifacts"
    out_dir.mkdir()

    # Make parity_runner write into our tmp_path by switching cwd so
    # Path("artifacts/parity_report.json") resolves inside tmp_path.
    monkeypatch.chdir(tmp_path)

    # _write_self_check_report signature: (ok: bool, failures: list[dict], explain=False, quiet=False)
    parity_runner._write_self_check_report(True, [], explain=False, quiet=False)

    path = out_dir / "parity_report.json"
    assert path.is_file()
    data = json.loads(path.read_text())
    assert data.get("type") == "self-check"
    assert data.get("ok") is True


def test_write_parity_report_creates_json(tmp_path, monkeypatch):
    """
    Similar to self-check: parity report writer should output JSON with expected keys.
    """
    out_dir = tmp_path / "artifacts"
    out_dir.mkdir()

    # Make parity_runner write into our tmp_path by switching cwd so
    # Path("artifacts/parity_report.json") resolves inside tmp_path.
    monkeypatch.chdir(tmp_path)

    lock = {"thresholds": {"coverage_min": 0.0}, "pytest_collection": {}}
    results = {"pytest": {"returncode": 0, "duration": 0.1, "passed": True}}
    failures = []
    tools = {"pytest": {}}
    coverage_rate = 1.0

    parity_runner._write_parity_report(lock, results, failures, tools, coverage_rate, explain=False)

    path = out_dir / "parity_report.json"
    assert path.is_file()
    data = json.loads(path.read_text())
    assert "thresholds" in data or "collection" in data
