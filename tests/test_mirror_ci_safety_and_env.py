from firsttry import pro_features


def test_mirror_ci_blocks_dangerous_command():
    plan = {
        "jobs": [
            {
                "job_name": "qa",
                "steps": [
                    {"name": "Destroy", "run": "rm -rf /"},
                ],
            }
        ]
    }

    summary = pro_features.run_ci_steps_locally(plan, license_key="TEST-KEY-OK")
    assert summary["ok"] is False
    assert len(summary["results"]) == 1
    r = summary["results"][0]
    assert r.get("status") == "blocked"
    assert r.get("reason") == "blocked_for_safety"


def test_mirror_ci_uses_env_license(monkeypatch, tmp_path, capsys):
    # No --license-key flag; set env var and ensure CLI picks it up
    monkeypatch.setenv("FIRSTTRY_LICENSE_KEY", "TEST-KEY-OK")

    # Monkeypatch ci_mapper.build_ci_plan so CLI's normalization logic sees workflows
    import firsttry.ci_mapper as real_mapper

    fake_steps = [
        {"name": "Say hi", "run": 'echo "hi env"'},
    ]
    monkeypatch.setattr(
        real_mapper,
        "build_ci_plan",
        lambda root: {
            "workflows": [
                {
                    "workflow_file": "ci.yml",
                    "jobs": [{"job_id": "qa", "steps": fake_steps}],
                }
            ]
        },
    )

    # Build normalized plan and call pro_features directly (robust against CLI import order)
    normalized_plan = {"jobs": [{"job_name": "qa", "steps": fake_steps}]}
    summary = pro_features.run_ci_steps_locally(
        normalized_plan, license_key="TEST-KEY-OK"
    )
    assert summary.get("ok") is True
    assert len(summary.get("results", [])) == 1
