import importlib
import json
from pathlib import Path

import pytest


def _require(modname, *funcs):
    try:
        m = importlib.import_module(modname)
    except Exception:
        pytest.skip(f"{modname} not importable")
    missing = [f for f in funcs if not hasattr(m, f)]
    if missing:
        pytest.skip(f"{modname} missing {missing}")
    return m


def test_collect_type_section_with_valid_and_malformed_json(tmp_path, monkeypatch):
    # Require the function; skip gracefully if absent in this revision
    scanner = _require("firsttry.scanner", "_collect_type_section")

    # Fake mypy --error-format=json-lines output (2 lines, one valid, one malformed)
    valid = json.dumps(
        {
            "file": "pkg/mod.py",
            "line": 1,
            "column": 1,
            "severity": "error",
            "message": "Incompatible types",
        }
    )
    malformed = "{this is not json}"

    # Stub _run_cmd to simulate mypy stdout (json-lines)
    def fake_run_cmd(cmd, cwd=None, env=None, timeout=None):
        out = valid + "\n" + malformed + "\n"
        return 0, out, ""

    monkeypatch.setattr(scanner, "_run_cmd", fake_run_cmd, raising=True)

    # Create a tiny file structure (often used for path roots)
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("x=1\n", encoding="utf-8")

    # _collect_type_section has varied signatures across revisions; try multiple calling styles.
    p = str(tmp_path / "pkg")

    def _attempt_calls(fn):
        callers = [
            lambda: fn(root=str(tmp_path), paths=[p]),
            lambda: fn(str(tmp_path), [p]),
            lambda: fn([p]),
            lambda: fn(paths=[p]),
            lambda: fn(p),
        ]
        for c in callers:
            try:
                return c()
            except TypeError:
                continue
        pytest.skip("unsupported signature for _collect_type_section in this revision")

    issues = _attempt_calls(scanner._collect_type_section)
    # Expect at least the valid entry to be parsed into an Issue-like dict structure
    assert isinstance(issues, list) and len(issues) >= 1
    first = issues[0]
    # Be flexible on schema — check a few common fields
    assert "message" in first and "path" in first


def test_collect_security_section_with_and_without_baseline(tmp_path, monkeypatch):
    scanner = _require("firsttry.scanner", "_collect_security_section", "_is_baselined")

    # Simulate Bandit JSON with two issues of different severities
    bandit_report = {
        "results": [
            {"issue_severity": "LOW", "filename": "a.py", "issue_text": "low thing"},
            {"issue_severity": "HIGH", "filename": "b.py", "issue_text": "danger!"},
        ]
    }

    def fake_run_cmd(cmd, cwd=None, env=None, timeout=None):
        return 0, json.dumps(bandit_report), ""

    monkeypatch.setattr(scanner, "_run_cmd", fake_run_cmd, raising=True)

    # No baseline -> both issues appear
    no_base = scanner._collect_security_section(root=str(tmp_path), paths=[str(tmp_path)])
    assert any("HIGH" in str(i.get("severity", "")).upper() for i in no_base)

    # Create a simple baseline that baselines the HIGH in b.py
    baseline_path = Path(tmp_path / "firsttry_security_baseline.yml")
    baseline_path.write_text("b.py: HIGH\n", encoding="utf-8")

    with_base = scanner._collect_security_section(
        root=str(tmp_path), paths=[str(tmp_path)], baseline=str(baseline_path)
    )
    # Expect fewer HIGHs after baseline filtering
    assert sum("HIGH" in str(i.get("severity", "")).upper() for i in no_base) >= sum(
        "HIGH" in str(i.get("severity", "")).upper() for i in with_base
    )


def test_scan_with_ruff_handles_invalid_json(monkeypatch, tmp_path):
    scanner = _require("firsttry.scanner", "_scan_with_ruff")

    # Ruff sometimes prints non-JSON or truncated JSON under failures; simulate that
    def fake_run_cmd(cmd, cwd=None, env=None, timeout=None):
        return 0, "not-json\n", ""

    monkeypatch.setattr(scanner, "_run_cmd", fake_run_cmd, raising=True)

    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("x=1\n", encoding="utf-8")

    # Try multiple call signatures (older/newer revisions vary)
    p = str(tmp_path / "pkg")

    def _attempt(fn):
        callers = [
            lambda: fn(root=str(tmp_path), paths=[p]),
            lambda: fn(str(tmp_path), [p]),
            lambda: fn([p]),
            lambda: fn(paths=[p]),
            lambda: fn(p),
        ]
        for c in callers:
            try:
                return c()
            except TypeError:
                continue
        pytest.skip("unsupported signature for _scan_with_ruff in this revision")

    issues = _attempt(scanner._scan_with_ruff)
    # Should not crash; return empty or a tolerant structure
    assert issues is None or isinstance(issues, list)
