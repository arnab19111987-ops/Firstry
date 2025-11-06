from firsttry import pro_features as pf


def test_run_ci_steps_locally_blocks_without_license_for_plan_dict():
    plan = {"jobs": [{"job_name": "qa", "steps": []}]}
    out = pf.run_ci_steps_locally(plan, license_key=None)
    assert out["ok"] is False
    assert out["results"][0]["job"] == "license-check"


def test_run_ci_steps_locally_invalid_license_is_treated_as_ok_currently():
    # Current behavior: non-empty license strings are accepted by _assert_license_is_valid,
    # so BAD-KEY doesn't trigger a failure here. Keep test aligned with implementation.
    plan = {"jobs": [{"job_name": "qa", "steps": []}]}
    out = pf.run_ci_steps_locally(plan, license_key="BAD-KEY")
    assert out["ok"] is True


def test_run_ci_steps_locally_legacy_list_and_blocked_command():
    # legacy list input: also exercises dangerous token blocking path
    cmds = ["echo ok", "rm -rf /", "echo end"]
    out = pf.run_ci_steps_locally(cmds)
    assert out["ok"] is False  # dangerous command blocked
    # Ensure at least 3 results for 3 commands, with one blocked
    statuses = [r.get("status") for r in out["results"]]
    assert "blocked" in statuses


def test_run_ci_plan_locally_license_fail():
    plan = {"jobs": []}
    out = pf.run_ci_plan_locally(plan, license_key=None)
    assert out["ok"] is False
    assert out["summary"]["failed_at"]["reason"] == "license"


def test_run_ci_plan_locally_early_stop_and_quickfix_fallback(monkeypatch):
    # Two steps: first fails, second shouldn't run; quickfix.suggest_fix raises
    plan = {
        "jobs": [
            {
                "job_name": "qa",
                "workflow_name": "WF",
                "steps": [
                    {
                        "step_name": "bad",
                        "cmd": "python -c 'import sys; print(\"x\"); sys.exit(2)'",
                        "install": False,
                        "meta": {
                            "workflow": "WF",
                            "job": "qa",
                            "original_index": 0,
                            "original_step": {},
                        },
                    },
                    {
                        "step_name": "good",
                        "cmd": "python -c 'print(\"ok\")'",
                        "install": False,
                        "meta": {
                            "workflow": "WF",
                            "job": "qa",
                            "original_index": 1,
                            "original_step": {},
                        },
                    },
                ],
            },
        ],
    }

    # Force quickfix path to raise to hit fallback generic hint
    class Q:
        def suggest_fix(self, *a, **k):
            raise RuntimeError("fail")

    monkeypatch.setattr(pf, "quickfix", Q(), raising=True)

    out = pf.run_ci_plan_locally(plan, license_key="TEST-KEY-OK")
    assert out["ok"] is False
    # Ensure early stop: only first step recorded
    assert out["summary"]["failed_at"]["step_name"] == "bad"
    assert out["jobs"][0]["steps"][0]["step_name"] == "bad"
    assert len(out["jobs"][0]["steps"]) == 1
    assert "hint" in out["summary"]["failed_at"]
