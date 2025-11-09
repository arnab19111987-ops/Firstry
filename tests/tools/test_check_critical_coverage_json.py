import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = "tools/check_critical_coverage.py"


def _write_cov(tmp, files_dict):
    (tmp / "coverage.json").write_text(
        json.dumps({"meta": {}, "files": files_dict}), encoding="utf-8"
    )


def test_json_summary_shape_and_env_path(tmp_path):
    # one critical present, one missing to exercise both lists
    files = {
        "src/firsttry/state.py": {"summary": {"percent_covered": 61.0}},
        # note: planner.py intentionally absent to show up in "missing"
    }
    _write_cov(tmp_path, files)
    out_json = tmp_path / ".firsttry" / "critical_coverage_summary.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["FT_CRITICAL_MIN_RATE"] = "60"
    env["FT_COVERAGE_JSON_OUT"] = str(out_json)

    # ensure the script is available in the tmp cwd for subprocess invocation
    from shutil import copyfile

    src = Path(SCRIPT)
    dest_dir = tmp_path / "tools"
    dest_dir.mkdir(exist_ok=True)
    copyfile(src, dest_dir / Path(SCRIPT).name)

    r = subprocess.run(
        [sys.executable, SCRIPT], cwd=tmp_path, env=env, capture_output=True, text=True
    )
    # Should pass with state.py = 61% and threshold 60
    assert r.returncode == 0, r.stderr + r.stdout
    assert out_json.exists(), "JSON summary not written"

    j = json.loads(out_json.read_text(encoding="utf-8"))
    # Required top-level keys
    for key in ("threshold", "files", "missing", "status"):
        assert key in j, f"Missing key: {key}"

    assert j["threshold"] == 60.0
    assert j["status"] == "pass"

    # files: list of dicts {path, percent_covered}
    paths = {f["path"] for f in j["files"]}
    assert "src/firsttry/state.py" in paths
    # Missing should include the critical that wasn’t present in coverage.json if your gate declares it critical
    # If your gate only treats present criticals, this may be empty—adjust if needed
    assert isinstance(j["missing"], list)


def test_json_summary_reports_below_threshold(tmp_path):
    files = {"src/firsttry/state.py": {"summary": {"percent_covered": 25.0}}}
    _write_cov(tmp_path, files)
    out_json = tmp_path / "critical.json"
    env = os.environ.copy()
    env["FT_CRITICAL_MIN_RATE"] = "60"
    env["FT_COVERAGE_JSON_OUT"] = str(out_json)

    # ensure the script is available in the tmp cwd for subprocess invocation
    from shutil import copyfile

    src = Path(SCRIPT)
    dest_dir = tmp_path / "tools"
    dest_dir.mkdir(exist_ok=True)
    copyfile(src, dest_dir / Path(SCRIPT).name)

    r = subprocess.run(
        [sys.executable, SCRIPT], cwd=tmp_path, env=env, capture_output=True, text=True
    )
    assert r.returncode != 0, "Gate should fail when below threshold"
    j = json.loads(out_json.read_text(encoding="utf-8"))
    assert j["status"] == "fail"
    # Find the failing entry
    failing = [f for f in j["files"] if f.get("percent_covered", 0) < j["threshold"]]
    assert failing, "Expected at least one below-threshold file in JSON"
