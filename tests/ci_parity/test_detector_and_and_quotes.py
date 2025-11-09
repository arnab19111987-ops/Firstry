from firsttry.ci_parity import detector


def test_detect_singleline_and_and_with_quotes(tmp_path, monkeypatch):
    wf = tmp_path / ".github/workflows/ci.yml"
    wf.parent.mkdir(parents=True, exist_ok=True)
    wf.write_text(
        "jobs:\n"
        "  lint:\n"
        "    steps:\n"
        '      - run: black --check src && ruff check && pytest -q -k "not slow"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("FT_REPO_ROOT", str(tmp_path))
    d = detector.detect()
    ids = {s["id"] for s in d.steps}
    assert {"black", "ruff", "pytest"}.issubset(ids)
