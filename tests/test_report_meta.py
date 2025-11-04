import json, os, sys, subprocess, tempfile


def test_report_contains_perf_meta():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    tmp.close()
    cmd = [sys.executable, "-m", "firsttry", "run", "--tier", "free-lite",
        "--report-json", tmp.name]
    env = os.environ.copy()
    env["FT_FORCE_REPORT_WRITE"] = "1"
    p = subprocess.run(cmd, text=True, capture_output=True, env=env)
    assert p.returncode == 0, f"firsttry run failed: {p.stderr}"

    data = json.load(open(tmp.name, encoding="utf-8"))
    meta = data.get("meta", {})
    # We don’t assert exact numbers, only presence & type
    assert "startup_s" in meta and isinstance(meta["startup_s"], (int, float))
    assert "to_first_tool_s" in meta and isinstance(meta["to_first_tool_s"], (int, float))
