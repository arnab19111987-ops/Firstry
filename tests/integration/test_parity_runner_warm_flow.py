import os
from pathlib import Path

import firsttry.ci_parity.parity_runner as pr


def test_parity_runner_warm_path_smoke_fallback(tmp_path, monkeypatch, capsys):
    # Prepare a fake artifacts directory
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()

    # Point ARTIFACTS to our tmp dir and ensure_dirs to create it
    monkeypatch.setattr(pr, "ARTIFACTS", artifacts)
    monkeypatch.setattr(pr, "ensure_dirs", lambda: artifacts.mkdir(exist_ok=True))

    # Track calls
    calls = {"run": []}

    # Fake run: behave differently depending on the invoked command
    def fake_run(cmd, timeout_s, explain=False):
        cmd_list = cmd if isinstance(cmd, list) else str(cmd).split()
        calls["run"].append(cmd_list)
        # If this is the testmon invocation, simulate "no tests collected" (rc=5)
        if any("--testmon" in str(x) for x in cmd_list):
            return 5, "no tests collected"
        # If this is the flaky invocation, shouldn't be called in this scenario
        if any("pytest-flaky" in str(x) for x in cmd_list):
            return 0, "flaky"
        # If this is the smoke invocation, simulate success
        if "-m" in cmd_list and "smoke" in cmd_list:
            # write a fake pytest-smoke.json to emulate pytest-json-report
            (artifacts / "pytest-smoke.json").write_text("{\"tests\": []}")
            return 0, "smoke ok"
        # Default: success
        return 0, "ok"

    monkeypatch.setattr(pr, "run", fake_run)
    monkeypatch.setattr(pr, "read_flaky_tests", lambda: [])
    monkeypatch.setattr(pr, "_collect_failures_from_json", lambda p: [])

    # Run warm_path which should exercise testmon -> smoke fallback
    rc = pr.warm_path(explain=False)

    # Ensure we returned success and that testmon+smoke were invoked
    assert rc == pr.EXIT_SUCCESS
    # At least one run was called for testmon and one for smoke
    assert any("--testmon" in " ".join(map(str, c)) for c in calls["run"])
    assert any("-m" in c and "smoke" in c for c in calls["run"])
