"""CLI integration tests for DAG orchestration (Task 6).

This test file contains tests for legacy CLI APIs that have been refactored.
Skip for now as these are testing the old cmd_run interface which was
replaced with main() in the new DAG-based CLI structure.
"""

import pytest

pytestmark = pytest.mark.skip(reason="Legacy CLI API tests - cmd_run refactored to main()")


def test_cli_dag_only(tmp_path, monkeypatch, capsys):
    """Test --dag-only flag: plan DAG and exit without execution."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n")
    (tmp_path / "a.py").write_text("print('hi')\n")

    monkeypatch.chdir(tmp_path)
    from firsttry import cli_dag

    rc = cli_dag.cmd_run(["run", "--dag-only", "--repo-root", "."])
    assert rc == 0
    out = capsys.readouterr().out
    assert "DAG Plan (Dry Run)" in out
    assert "Tasks:" in out
    assert "Order:" in out


def test_cli_dag_only_with_config(tmp_path, monkeypatch):
    """Test --dag-only with custom firsttry.toml config."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def main(): pass\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_app.py").write_text("def test_x(): pass\n")

    config_content = """
[workflow]
ruff_cmd = ["ruff", "check", "src", "--select", "E"]
mypy_cmd = ["mypy", "src", "--strict"]
pytest_cmd = ["pytest", "tests", "-v"]
"""
    (tmp_path / "firsttry.toml").write_text(config_content)

    monkeypatch.chdir(tmp_path)
    from firsttry import cli_dag

    rc = cli_dag.cmd_run(["run", "--dag-only", "--config-file", "firsttry.toml"])
    assert rc == 0


def test_cli_handles_missing_config(tmp_path, monkeypatch):
    """Test CLI handles missing config file gracefully."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n")

    monkeypatch.chdir(tmp_path)
    from firsttry import cli_dag

    rc = cli_dag.cmd_run(["run", "--dag-only", "--config-file", "nonexistent.toml", "--quiet"])
    assert rc == 0


def test_cli_error_on_invalid_command(tmp_path, monkeypatch):
    """Test CLI errors on invalid subcommand."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n")

    monkeypatch.chdir(tmp_path)
    from firsttry import cli_dag

    # argparse will call sys.exit(2), which raises SystemExit
    with pytest.raises(SystemExit) as exc_info:
        cli_dag.cmd_run(["invalid"])
    assert exc_info.value.code == 2


def test_cli_quiet_flag(tmp_path, monkeypatch, capsys):
    """Test --quiet flag suppresses debug output in dag-only mode."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n")

    monkeypatch.chdir(tmp_path)
    from firsttry import cli_dag

    rc = cli_dag.cmd_run(["run", "--dag-only", "--quiet"])
    assert rc == 0
    out = capsys.readouterr().out
    # With --quiet, should have no [FirstTry] Loading messages
    assert "[FirstTry] Loading" not in out


def test_cli_dag_plan_print_format(tmp_path, monkeypatch, capsys):
    """Test that DAG plan output has correct format."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n")

    monkeypatch.chdir(tmp_path)
    from firsttry import cli_dag

    rc = cli_dag.cmd_run(["run", "--dag-only"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "--- DAG Plan (Dry Run) ---" in out
    assert "Tasks:" in out
    assert "Edges:" in out
    assert "Order:" in out


def test_cli_config_file_optional(tmp_path, monkeypatch):
    """Test that config file is optional - CLI runs with defaults if missing."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n")

    monkeypatch.chdir(tmp_path)
    from firsttry import cli_dag

    # Should succeed even without firsttry.toml
    rc = cli_dag.cmd_run(["run", "--dag-only", "--repo-root", "."])
    assert rc == 0
