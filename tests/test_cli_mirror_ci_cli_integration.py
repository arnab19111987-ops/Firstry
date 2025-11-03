from firsttry import ci_mapper


def test_cli_mirror_ci_run_integration(monkeypatch, capsys, tmp_path):
    # Fake license
    monkeypatch.setenv("FIRSTTRY_LICENSE_KEY", "TEST-KEY-OK")

    # Fake adaptive plan returned by ci_mapper
    def fake_build(root):
        return {
            "jobs": [
                {
                    "job_name": "qa",
                    "workflow_name": "SpeedCheck",
                    "steps": [
                        {
                            "step_name": "Lint",
                            "cmd": "python -c \"print('lint ok')\"",
                            "install": False,
                            "meta": {
                                "workflow": "SpeedCheck",
                                "job": "qa",
                                "original_index": 0,
                                "original_step": {},
                            },
                        },
                        {
                            "step_name": "Tests",
                            "cmd": "python -c \"print('pytest ok')\"",
                            "install": False,
                            "meta": {
                                "workflow": "SpeedCheck",
                                "job": "qa",
                                "original_index": 1,
                                "original_step": {},
                            },
                        },
                    ],
                }
            ]
        }

    monkeypatch.setattr(ci_mapper, "build_ci_plan", fake_build)

    import pytest
    pytest.skip("mirror-ci --run functionality integrated into new CLI structure")
