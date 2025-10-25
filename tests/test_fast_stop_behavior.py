import os
from firsttry import pro_features


class _DummyQuickfix:
    @staticmethod
    def suggest_fix(cmd: str, stdout: str, stderr: str) -> str:
        # deterministic so we don't depend on heuristic logic for this test
        return "dummy hint"


def test_runner_stops_after_first_failure(monkeypatch):
    """
    The pro runner must:
    - stop executing steps after the first failure (speed guarantee)
    - report only the steps that actually ran
    - surface the failing step in summary.failed_at
    """

    # Pretend we have a valid license
    license_key = "TEST-KEY-OK"

    # Inject deterministic quickfix to avoid None / randomness
    monkeypatch.setattr(pro_features, "quickfix", _DummyQuickfix, raising=False)

    # Plan with two steps in one job:
    #   step 1 -> fails with exit code 7
    #   step 2 -> would succeed, but MUST NOT RUN
    plan = {
        "jobs": [
            {
                "job_name": "qa",
                "workflow_name": "wf",
                "steps": [
                    {
                        "step_name": "failing step",
                        "cmd": 'python -c "import sys; sys.exit(7)"',
                        "install": False,
                        "meta": {
                            "workflow": "wf",
                            "job": "qa",
                            "original_index": 0,
                            "original_step": {},
                        },
                    },
                    {
                        "step_name": "should never run",
                        "cmd": 'python -c "print(\'SHOULD_NOT_RUN\')"',
                        "install": False,
                        "meta": {
                            "workflow": "wf",
                            "job": "qa",
                            "original_index": 1,
                            "original_step": {},
                        },
                    },
                ],
            }
        ]
    }

    res = pro_features.run_ci_plan_locally(plan, license_key=license_key)

    # Overall should be marked not ok
    assert res["ok"] is False

    # Verify we only ran the first step
    steps_executed = res["jobs"][0]["steps"]
    assert len(steps_executed) == 1, "Runner did not stop after failure"
    assert steps_executed[0]["step_name"] == "failing step"

    # Verify summary.failed_at matches that failed step
    failed_at = res["summary"]["failed_at"]
    assert failed_at is not None
    assert failed_at["step_name"] == "failing step"
    assert failed_at["returncode"] != 0
    assert "dummy hint" in failed_at["hint"]  # quickfix was injected

    # Sanity: confirm we didn't accidentally include 'should never run'
    assert "SHOULD_NOT_RUN" not in steps_executed[0]["stdout"]
