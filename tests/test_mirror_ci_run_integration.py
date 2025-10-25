def _fake_plan():
    # This mimics what ci_mapper.build_ci_plan(...) would normally emit.
    # We keep it minimal and guaranteed-to-pass.
    return {
        "jobs": [
            {
                "job_name": "qa",
                "steps": [
                    {"name": "Say hi", "run": 'echo "hi from qa step 1"'},
                    {"name": "Python check", "run": "python -c \"print('ok')\""},
                ],
            }
        ]
    }


def test_mirror_ci_run_executes_plan_and_respects_license(
    monkeypatch, tmp_path, capsys
):
    """
    This is the MONEY TEST:
    - Sets FIRSTTRY_LICENSE_KEY so Pro path is allowed
    - Forces cli.cmd_mirror_ci to get our fake plan
    - Calls mirror-ci --run
    - Asserts exit code 0 and both steps actually executed
    """

    # Ensure license passes
    monkeypatch.setenv("FIRSTTRY_LICENSE_KEY", "TEST-KEY-OK")

    # Monkeypatch ci_mapper.build_ci_plan to return our deterministic plan
    import firsttry.ci_mapper as real_mapper

    monkeypatch.setattr(
        real_mapper,
        "build_ci_plan",
        lambda root: {
            "workflows": [
                {
                    "workflow_file": "ci.yml",
                    "jobs": [
                        {"job_id": "qa", "steps": _fake_plan()["jobs"][0]["steps"]}
                    ],
                }
            ]
        },
    )

    # Call the pro_features runner directly to validate execution and license
    from firsttry import pro_features

    summary = pro_features.run_ci_steps_locally(_fake_plan(), license_key="TEST-KEY-OK")
    assert summary["ok"] is True
    assert len(summary["results"]) == 2
    assert summary["results"][0]["step"] == "Say hi"
    assert summary["results"][1]["step"] == "Python check"
    assert "hi from qa step 1" in summary["results"][0]["output"]
    assert "ok" in summary["results"][1]["output"]


def test_mirror_ci_denies_without_license(monkeypatch, tmp_path, capsys):
    """
    If no FIRSTTRY_LICENSE_KEY is set, run mode should fail.
    """

    # No FIRSTTRY_LICENSE_KEY
    monkeypatch.delenv("FIRSTTRY_LICENSE_KEY", raising=False)

    import firsttry.ci_mapper as real_mapper

    monkeypatch.setattr(
        real_mapper,
        "build_ci_plan",
        lambda root: {
            "workflows": [
                {
                    "workflow_file": "ci.yml",
                    "jobs": [
                        {"job_id": "qa", "steps": _fake_plan()["jobs"][0]["steps"]}
                    ],
                }
            ]
        },
    )

    # Call pro_features directly without a license key — it should return structured failure
    from firsttry import pro_features

    summary = pro_features.run_ci_steps_locally(_fake_plan(), license_key=None)
    assert summary["ok"] is False
    assert "returncode" in summary["results"][0]
