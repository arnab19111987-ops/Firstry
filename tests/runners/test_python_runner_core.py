"""
Unit tests for lightweight python runner helpers.

Goal:
- Ensure helper functions build expected paths / find ci commands.
"""

from firsttry.runners import python as python_runner


def test_find_ci_cmd_prefers_ci_plan():
    ci_plan = [{"tool": "pytest", "cmd": "pytest -q"}, {"tool": "ruff", "cmd": "ruff check ."}]
    assert python_runner._find_ci_cmd(ci_plan, "pytest") == "pytest -q"
    assert python_runner._find_ci_cmd(ci_plan, "ruff") == "ruff check ."
    assert python_runner._find_ci_cmd(ci_plan, "mypy") is None


def test_discover_test_paths_tmpdir(tmp_path):
    # no tests dir -> create tests dir
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "tests").mkdir()
    paths = python_runner._discover_test_paths(str(repo))
    assert any(p.endswith("tests") or p == "tests" or p == str(repo / "tests") for p in paths)


def test_discover_python_roots_tmpdir(tmp_path):
    repo = tmp_path / "repo2"
    repo.mkdir()
    (repo / "pyproject.toml").write_text('[tool.poetry]\nname = "x"\n')
    roots = python_runner._discover_python_roots(str(repo))
    assert (
        roots and any("pyproject.toml" not in r for r in roots) or roots == ["."] or len(roots) >= 1
    )
