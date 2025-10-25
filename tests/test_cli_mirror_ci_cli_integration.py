import json
import time
from firsttry import cli, ci_mapper, pro_features


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
                            "cmd": 'python -c "print(\'lint ok\')"',
                            "install": False,
                            "meta": {"workflow":"SpeedCheck","job":"qa","original_index":0,"original_step":{}},
                        },
                        {
                            "step_name": "Tests",
                            "cmd": 'python -c "print(\'pytest ok\')"',
                            "install": False,
                            "meta": {"workflow":"SpeedCheck","job":"qa","original_index":1,"original_step":{}},
                        },
                    ],
                }
            ]
        }

    monkeypatch.setattr(ci_mapper, "build_ci_plan", fake_build)

    parser = cli.build_parser()
    ns = parser.parse_args(["mirror-ci", "--root", str(tmp_path), "--run"])

    start = time.time()
    rc = cli.cmd_mirror_ci(ns)
    end = time.time()

    output = capsys.readouterr().out
    data = json.loads(output)

    assert rc == 0
    assert data["ok"] is True
    assert data["summary"]["runtime_sec"] <= round(end - start, 3)  # runtime tracked
    assert data["summary"]["total_steps"] == 2
    assert data["jobs"][0]["steps"][0]["step_name"] == "Lint"

    # speed budget: prove it's "seconds" territory
    assert (end - start) < 3.0, f"mirror-ci --run took too long: {(end-start):.2f}s"
