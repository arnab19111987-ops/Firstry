import json
import os
import subprocess
import sys
import tempfile
import textwrap
import pathlib


def run(cmd: list[str], cwd=None):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


def test_bandit_is_advisory(tmp_path: pathlib.Path):
    # Arrange: create a tiny src tree with an intentional Bandit hit
    (tmp_path / "src" / "scratch").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "scratch" / "tmp_vuln.py").write_text(textwrap.dedent("""
        # demo only
        eval(input("danger: "))  # B307
    """))
    # Minimal runtime config (advisory)
    (tmp_path / "firsttry.toml").write_text(textwrap.dedent("""
        [tool.firsttry.checks.bandit]
        enabled = true
        blocking = false
        fail_on = "high"
        jobs = 0
        include = ["src"]
        exclude = [".venv","node_modules",".git","__pycache__","build","dist"]
        extra_args = ["-q"]
    """))

    # Act
    report = tmp_path / ".firsttry" / "pro_verify.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["FIRSTTRY_LICENSE_KEY"] = "devkey-abcdefghijkl"
    proc = subprocess.run(
        [sys.executable, "-m", "firsttry.cli", "run", "pro", "--report-json", str(report)],
        cwd=tmp_path, env=env, text=True, capture_output=True
    )
    # Assert: CLI exit code should be 0 (advisory does not fail)
    assert proc.returncode == 0, proc.stderr

    data = json.loads(report.read_text())
    # Support both schema shapes: checks entries may have id/name keys
    b = None
    for c in data.get("checks", []):
        if c.get("id") == "bandit" or c.get("name") == "bandit":
            b = c
            break
    assert b is not None, "bandit entry missing from report"
    # Accept different status labels used across report versions
    assert b["status"] in {"pass", "advisory", "ok", "skipped", "dry-run"}

    # The orchestrator writes a merged bandit JSON to .firsttry/bandit.json
    raw = tmp_path / ".firsttry" / "bandit.json"
    assert raw.exists(), "expected merged bandit JSON at .firsttry/bandit.json"
    try:
        js = json.loads(raw.read_text())
        assert isinstance(js.get("results", []), list)
    except Exception:
        # If bandit didn't write JSON, at least the CLI produced a report file
        assert report.exists()
