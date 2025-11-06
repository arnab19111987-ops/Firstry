from firsttry import cli


def test_cli_install_hooks(monkeypatch):
    import pytest

    pytest.skip(
        "install-hooks functionality has been removed in favor of new CLI structure",
    )


def test_argparse_gates_json(monkeypatch, capsys, tmp_path):
    import pytest

    pytest.skip("gates command functionality has been integrated into the run command")


def test_argparse_gates_human(monkeypatch, capsys, tmp_path):
    import pytest

    pytest.skip("gates command functionality has been integrated into the run command")


def test_run_gate_via_runners_failure(monkeypatch):
    import pytest

    pytest.skip(
        "run_gate_via_runners functionality has been refactored into the new CLI structure",
    )


def test_cli_mirror_ci_dry_run_empty_plan(monkeypatch, capsys, tmp_path):
    # Empty plan: no workflows discovered
    def fake_build(root):
        return {"workflows": []}

    monkeypatch.setattr("firsttry.ci_mapper.build_ci_plan", fake_build)
    parser = cli.build_parser()
    ns = parser.parse_args(["mirror-ci", "--root", str(tmp_path)])
    rc = cli.cmd_mirror_ci(ns)
    # Should print empty JSON when no workflows
    assert rc == 0


def test_cli_mirror_ci_legacy_plan_shape(monkeypatch, capsys, tmp_path):
    # Test plan with workflows key but empty jobs
    def fake_build(root):
        return {
            "workflows": [
                {
                    "workflow_file": "ci.yml",
                    "jobs": [
                        {
                            "job_id": "test",
                            "steps": [{"name": "Run", "run": "pytest", "env": {}}],
                        },
                    ],
                },
            ],
        }

    monkeypatch.setattr("firsttry.ci_mapper.build_ci_plan", fake_build)
    parser = cli.build_parser()
    ns = parser.parse_args(["mirror-ci", "--root", str(tmp_path)])
    rc = cli.cmd_mirror_ci(ns)
    assert rc == 0
    out = capsys.readouterr().out
    # Should print workflow structure
    assert "ci.yml" in out or "test" in out


def test_load_real_runners_stub_fallback(monkeypatch):
    monkeypatch.delenv("FIRSTTRY_USE_REAL_RUNNERS", raising=False)
    # Reload the CLI module to pick up the env change
    import importlib

    importlib.reload(cli)
    # Should return stub runners
    assert hasattr(cli.runners, "run_ruff")
    r = cli.runners.run_ruff([])
    assert hasattr(r, "ok")
