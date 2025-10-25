from firsttry import pro_features


def _fake_plan_two_steps_ok_then_fail():
    return {
        "jobs": [
            {
                "job_name": "qa",
                "workflow_name": "UnitPipeline",
                "steps": [
                    {
                        "step_name": "Echo ok",
                        "cmd": "python -c \"print('hello')\"",
                        "install": False,
                        "meta": {
                            "workflow": "UnitPipeline",
                            "job": "qa",
                            "original_index": 0,
                            "original_step": {"run": "python -c ..."},
                        },
                    },
                    {
                        "step_name": "This will fail",
                        "cmd": 'python -c "import sys; sys.exit(42)"',
                        "install": False,
                        "meta": {
                            "workflow": "UnitPipeline",
                            "job": "qa",
                            "original_index": 1,
                            "original_step": {"run": "python -c ..."},
                        },
                    },
                    {
                        "step_name": "Should never run",
                        "cmd": "python -c \"print('NEVER')\"",
                        "install": False,
                        "meta": {
                            "workflow": "UnitPipeline",
                            "job": "qa",
                            "original_index": 2,
                            "original_step": {"run": "python -c ..."},
                        },
                    },
                ],
            }
        ]
    }


def test_run_ci_plan_locally_fast_fail_and_precise_error(monkeypatch):
    # valid license so we don't get blocked
    license_key = "TEST-KEY-OK"

    plan = _fake_plan_two_steps_ok_then_fail()
    result = pro_features.run_ci_plan_locally(plan, license_key)

    # Should report overall failure
    assert result["ok"] is False
    assert "summary" in result
    assert result["summary"]["failed_at"] is not None

    failed = result["summary"]["failed_at"]
    # Check failure mapping is precise
    assert failed["workflow_name"] == "UnitPipeline"
    assert failed["job_name"] == "qa"
    assert failed["step_name"] == "This will fail"
    assert "sys.exit(42)" in failed["cmd"]
    assert failed["returncode"] != 0
    assert "hint" in failed

    # Steps actually run: first 2 only, not the 3rd
    job_report = result["jobs"][0]
    assert len(job_report["steps"]) == 2
    assert job_report["steps"][0]["step_name"] == "Echo ok"
    assert job_report["steps"][0]["returncode"] == 0
    assert job_report["steps"][1]["step_name"] == "This will fail"
    assert job_report["steps"][1]["returncode"] != 0


def test_run_ci_plan_locally_blocks_without_license():
    bad_license = None
    plan = _fake_plan_two_steps_ok_then_fail()
    result = pro_features.run_ci_plan_locally(plan, bad_license)

    # Should immediately refuse Pro execution
    assert result["ok"] is False
    assert result["summary"]["failed_at"]["reason"] == "license"
    assert result["summary"]["total_steps"] == 0
    assert result["jobs"] == []
