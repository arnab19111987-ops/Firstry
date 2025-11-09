import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = "tools/check_critical_coverage.py"


def write_cov(tmp, files_dict):
    data = {"meta": {}, "files": files_dict}
    (tmp / "coverage.json").write_text(json.dumps(data), encoding="utf-8")


def run_gate(tmp, min_rate="30"):
    env = os.environ.copy()
    env["FT_CRITICAL_MIN_RATE"] = min_rate
    # Ensure the gate script is available in the tmp cwd (tests run in an isolated tmpdir)
    from shutil import copyfile

    src = Path(SCRIPT)
    dest_dir = tmp / "tools"
    dest_dir.mkdir(exist_ok=True)
    copyfile(src, dest_dir / Path(SCRIPT).name)
    return subprocess.run(
        [sys.executable, SCRIPT], cwd=tmp, env=env, capture_output=True, text=True
    )


def test_gate_passes_with_minimal_coverage(tmp_path):
    # Critical file present with sufficient % covered
    files = {"src/firsttry/state.py": {"summary": {"percent_covered": 42.0}}}
    write_cov(tmp_path, files)
    r = run_gate(tmp_path, "30")
    assert r.returncode == 0, r.stderr + r.stdout
    assert "OK" in (r.stdout + r.stderr)


def test_gate_fails_when_below_threshold(tmp_path):
    files = {"src/firsttry/state.py": {"summary": {"percent_covered": 25.0}}}
    write_cov(tmp_path, files)
    r = run_gate(tmp_path, "30")
    assert r.returncode != 0
    assert "below threshold" in (r.stdout + r.stderr).lower()


def test_gate_fails_when_critical_file_missing(tmp_path):
    # No critical file at all; gate should fail and name which is missing
    files = {"src/firsttry/not_critical.py": {"summary": {"percent_covered": 99.0}}}
    write_cov(tmp_path, files)
    r = run_gate(tmp_path, "30")
    assert r.returncode != 0
    out = (r.stdout + r.stderr).lower()
    assert "missing" in out or "not found" in out
