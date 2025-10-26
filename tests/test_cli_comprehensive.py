from click.testing import CliRunner

from firsttry import cli


def test_cli_install_hooks(monkeypatch):
    # Mock install_git_hooks to avoid actual git operations
    def fake_install():
        return ".git/hooks/pre-commit", ".git/hooks/pre-push"

    monkeypatch.setattr("firsttry.hooks.install_git_hooks", fake_install)
    runner = CliRunner()
    result = runner.invoke(cli.main, ["install-hooks"])
    assert result.exit_code == 0
    assert "Installed Git hooks" in result.output


def test_argparse_gates_json(monkeypatch, capsys, tmp_path):
    # Mock run_all_gates
    def fake_run_all_gates(root):
        return {
            "ok": True,
            "results": [{"gate": "Lint", "ok": True, "status": "PASS"}],
        }

    monkeypatch.setattr("firsttry.gates.run_all_gates", fake_run_all_gates)
    parser = cli.build_parser()
    ns = parser.parse_args(["gates", "--root", str(tmp_path), "--json"])
    rc = cli.cmd_gates(ns)
    assert rc == 0
    out = capsys.readouterr().out
    assert '"ok": true' in out.lower()


def test_argparse_gates_human(monkeypatch, capsys, tmp_path):
    def fake_run_all_gates(root):
        return {
            "ok": False,
            "results": [{"gate": "Lint", "ok": False, "status": "FAIL"}],
        }

    monkeypatch.setattr("firsttry.gates.run_all_gates", fake_run_all_gates)
    parser = cli.build_parser()
    ns = parser.parse_args(["gates", "--root", str(tmp_path)])
    rc = cli.cmd_gates(ns)
    assert rc == 1
    out = capsys.readouterr().out
    assert "FirstTry Gates Report" in out


def test_run_gate_via_runners_failure(monkeypatch):
    # Force a runner to fail
    def fake_ruff(*a, **k):
        import types

        return types.SimpleNamespace(
            ok=False, name="ruff", duration_s=0.1, stdout="", stderr="error", cmd=()
        )

    monkeypatch.setattr(cli.runners, "run_ruff", fake_ruff)
    text, code = cli._run_gate_via_runners("pre-commit")
    assert code == 1
    assert "BLOCKED" in text


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
                        }
                    ],
                }
            ]
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
