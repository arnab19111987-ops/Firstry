import firsttry.smart_pytest as sp


def test_build_pytest_command_smart_when_failed(monkeypatch):
    # If get_failed_tests returns something, command should include --lf
    monkeypatch.setattr(sp, "get_failed_tests", lambda repo: ["tests/test_foo.py::test_bar"])
    cmd = sp.build_pytest_command(repo_root=".", mode="smart")
    assert any("--lf" in part or part == "--lf" for part in cmd)


def test_build_pytest_command_smoke_uses_smoke_tests(monkeypatch, tmp_path):
    # Create a tests dir with a test file so smoke mode picks it up
    td = tmp_path / "tests"
    td.mkdir()
    (td / "test_basic.py").write_text("def test_a():\n    assert True\n")

    cmd = sp.build_pytest_command(repo_root=str(tmp_path), mode="smoke")
    # Should include at least one file path (relative)
    assert any(str(part).endswith("test_basic.py") for part in cmd)


def test_build_pytest_command_parallel_flag(monkeypatch):
    # If xdist is present, -n auto should be added when parallel=True
    monkeypatch.setattr(sp, "has_pytest_xdist", lambda repo: True)
    cmd = sp.build_pytest_command(repo_root=".", mode="full", parallel=True)
    assert "-n" in cmd and "auto" in cmd
