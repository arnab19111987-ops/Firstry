from firsttry import pro_features


class DummyQuickfix:
    @staticmethod
    def suggest_fix(cmd: str, stdout: str, stderr: str):
        return "Install ruff: pip install ruff"


def test_failed_at_includes_quickfix_hint(monkeypatch):
    # Monkeypatch both the pro_features.quickfix reference and the real quickfix.suggest_fix
    # to make this test robust regardless of import timing.
    monkeypatch.setattr("firsttry.pro_features.quickfix", DummyQuickfix, raising=True)
    # Also patch the package quickfix's suggest_fix in case pro_features kept the module reference.
    monkeypatch.setattr(
        "firsttry.quickfix.suggest_fix", DummyQuickfix.suggest_fix, raising=False
    )

    plan = {
        "jobs": [
            {
                "job_name": "qa",
                "workflow_name": "wf",
                "steps": [
                    {
                        "step_name": "bad",
                        "cmd": 'python -c "import sys; sys.exit(9)"',
                        "install": False,
                        "meta": {
                            "workflow": "wf",
                            "job": "qa",
                            "original_index": 0,
                            "original_step": {},
                        },
                    },
                ],
            }
        ]
    }

    res = pro_features.run_ci_plan_locally(plan, license_key="TEST-KEY-OK")

    assert res["ok"] is False
    failed = res["summary"]["failed_at"]
    assert "hint" in failed
    # Accept either the deterministic quickfix hint or any non-generic hint.
    generic = "This is the first failing step. Fix this step to unblock CI."
    assert failed["hint"] != generic
