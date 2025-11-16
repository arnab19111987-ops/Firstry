"""
Unit tests for the parity runner warm-path logic.

These tests monkeypatch `parity_runner.run` to avoid running real pytest
and instead write small JSON reports into the artifacts directory to
exercise the decision logic in `warm_path`.
"""

import json
from pathlib import Path

from firsttry.ci_parity import parity_runner


def _make_json_report(path: Path, tests: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"tests": tests}))


def test_warm_path_testmon_pass(monkeypatch, tmp_path):
    """When testmon returns rc=0 and no failures, warm_path should succeed."""
    monkeypatch.chdir(tmp_path)

    # fake run will be called once for testmon; it should create pytest-warm.json
    def fake_run(cmd, timeout_s=0, explain=False):
        # find json-report-file arg
        for part in cmd:
            if isinstance(part, str) and part.startswith("--json-report-file="):
                _, val = part.split("=", 1)
                p = Path(val)
                _make_json_report(p, [{"nodeid": "tests/test_a.py::test_ok", "outcome": "passed"}])
                break
        return 0, ""

    monkeypatch.setattr(parity_runner, "run", fake_run)

    rc = parity_runner.warm_path(explain=False)
    assert rc == parity_runner.EXIT_SUCCESS


def test_warm_path_no_tests_then_smoke(monkeypatch, tmp_path):
    """If testmon collects no tests (rc=5) and there are no flakies, warm_path should run smoke and succeed."""
    monkeypatch.chdir(tmp_path)

    calls = {"step": 0}

    def fake_run(cmd, timeout_s=0, explain=False):
        # Step 1: testmon -> rc 5
        if calls["step"] == 0:
            # write empty report (no tests)
            for part in cmd:
                if isinstance(part, str) and part.startswith("--json-report-file="):
                    _, val = part.split("=", 1)
                    p = Path(val)
                    _make_json_report(p, [])
                    break
            calls["step"] += 1
            return 5, ""

        # Step 3: smoke -> succeed
        if calls["step"] == 1:
            for part in cmd:
                if isinstance(part, str) and part.startswith("--json-report-file="):
                    _, val = part.split("=", 1)
                    p = Path(val)
                    _make_json_report(
                        p, [{"nodeid": "tests/test_smoke.py::test_smoke", "outcome": "passed"}]
                    )
                    break
            calls["step"] += 1
            return 0, ""

        return 1, ""

    monkeypatch.setattr(parity_runner, "run", fake_run)
    # ensure no flaky tests
    monkeypatch.setattr(parity_runner, "read_flaky_tests", lambda: [])

    rc = parity_runner.warm_path(explain=False)
    assert rc == parity_runner.EXIT_SUCCESS


def test_warm_path_no_tests_with_flaky(monkeypatch, tmp_path):
    """If testmon collected no tests but there's a flaky list, run flaky-only and succeed."""
    monkeypatch.chdir(tmp_path)

    calls = {"step": 0}

    def fake_run(cmd, timeout_s=0, explain=False):
        # testmon -> rc 5
        if calls["step"] == 0:
            for part in cmd:
                if isinstance(part, str) and part.startswith("--json-report-file="):
                    _, val = part.split("=", 1)
                    p = Path(val)
                    _make_json_report(p, [])
                    break
            calls["step"] += 1
            return 5, ""

        # flaky run -> succeed and write pytest-flaky.json
        if calls["step"] == 1:
            for part in cmd:
                if isinstance(part, str) and part.startswith("--json-report-file="):
                    _, val = part.split("=", 1)
                    p = Path(val)
                    _make_json_report(
                        p, [{"nodeid": "tests/test_x.py::test_fail", "outcome": "passed"}]
                    )
                    break
            calls["step"] += 1
            return 0, ""

        return 1, ""

    monkeypatch.setattr(parity_runner, "run", fake_run)
    monkeypatch.setattr(parity_runner, "read_flaky_tests", lambda: ["tests/test_x.py::test_fail"])

    rc = parity_runner.warm_path(explain=False)
    assert rc == parity_runner.EXIT_SUCCESS


def test_warm_path_fails_on_testmon_error(monkeypatch, tmp_path):
    """If testmon returns rc other than 0 or 5, warm_path should return TEST_FAILED."""
    monkeypatch.chdir(tmp_path)

    def fake_run(cmd, timeout_s=0, explain=False):
        # write a failing report
        for part in cmd:
            if isinstance(part, str) and part.startswith("--json-report-file="):
                _, val = part.split("=", 1)
                p = Path(val)
                _make_json_report(
                    p, [{"nodeid": "tests/test_a.py::test_fail", "outcome": "failed"}]
                )
                break
        return 1, ""

    monkeypatch.setattr(parity_runner, "run", fake_run)

    rc = parity_runner.warm_path(explain=False)
    assert rc == parity_runner.EXIT_TEST_FAILED
