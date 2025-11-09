from firsttry.ci_parity import detector


def test_detect_from_pyproject(tmp_path, monkeypatch):
    repo = tmp_path
    (repo / "pyproject.toml").write_text(
        """
[tool.black]
line-length = 100
[tool.ruff]
line-length = 100
[tool.mypy]
python_version = "3.11"
[tool.pytest.ini_options]
addopts = "-q"
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("FT_REPO_ROOT", str(repo))
    d = detector.detect()
    ids = [s["id"] for s in d.steps]
    assert {"black", "ruff", "mypy", "pytest"}.issubset(ids)
