from firsttry.ci_parity import detector


def test_detect_coverage_threshold_from_pyproject(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.coverage.run]
branch = true
[tool.coverage.report]
fail_under = 83
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("FT_REPO_ROOT", str(tmp_path))
    d = detector.detect()
    assert any(s.get("id") == "coverage-threshold" and s.get("threshold") == 83 for s in d.steps)
