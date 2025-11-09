import asyncio
import json
from pathlib import Path

from firsttry import smart_pytest as sp


def test_get_pytest_cache_dir():
    p = sp.get_pytest_cache_dir("/repo/root")
    assert isinstance(p, Path)
    assert str(p).endswith(".pytest_cache")


def test_get_failed_tests_and_smoke_and_testfile_mapping(tmp_path, monkeypatch):
    repo = tmp_path

    # create pytest cache structure with lastfailed
    cache_dir = repo / ".pytest_cache" / "v" / "cache"
    cache_dir.mkdir(parents=True)
    failed = {"tests/test_sample.py::test_one": {}}
    (cache_dir / "lastfailed").write_text(json.dumps(failed))

    res = sp.get_failed_tests(str(repo))
    assert isinstance(res, list)
    assert "tests/test_sample.py::test_one" in res

    # create tests/test_mymodule.py to exercise get_test_files_for_changes
    tests_dir = repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_mymodule.py").write_text("def test_x(): pass\n")

    out = sp.get_test_files_for_changes(str(repo), ["src/mymodule.py"])
    # should map to tests/test_mymodule.py
    assert any("test_mymodule.py" in p for p in out)

    # smoke tests detection
    (tests_dir / "test_smoke.py").write_text("def test_smoke(): pass\n")
    smoke = sp.get_smoke_tests(str(repo))
    assert any("test_smoke.py" in s for s in smoke)


def test_build_pytest_command_modes(monkeypatch, tmp_path):
    repo = str(tmp_path)
    # force has_pytest_xdist False for deterministic command
    monkeypatch.setattr(sp, "has_pytest_xdist", lambda repo_root: False)

    cmd = sp.build_pytest_command(repo_root=repo, mode="smoke")
    assert "-x" in cmd or any("test_" in c for c in cmd)

    cmd2 = sp.build_pytest_command(repo_root=repo, mode="failed")
    assert "--lf" in cmd2

    cmd3 = sp.build_pytest_command(repo_root=repo, mode="full")
    assert cmd3[0] == "python"


def test_run_smart_pytest_cache_hit(monkeypatch, tmp_path):
    """Run the coroutine synchronously via asyncio.run to avoid pytest-asyncio dependency."""
    repo = str(tmp_path)

    # monkeypatch cache functions to simulate cache hit
    monkeypatch.setattr(sp.ft_cache, "sha256_of_paths", lambda paths: "abc")
    monkeypatch.setattr(sp.ft_cache, "is_tool_cache_valid", lambda repo_root, tool, h: True)

    res = asyncio.run(
        sp.run_smart_pytest(repo_root=repo, changed_files=None, mode="smart", use_cache=True)
    )
    assert res["cached"] is True
    assert res["status"] == "ok"
