from __future__ import annotations

import json
from pathlib import Path

import firsttry.ci_parity.cache_utils as cache_utils


def test_read_flaky_tests_missing_file(monkeypatch, tmp_path):
    # Point FLAKY_FILE to a non-existent file in tmp_path
    fake = tmp_path / "ci" / "flaky_tests.json"
    monkeypatch.setattr(cache_utils, "FLAKY_FILE", fake, raising=False)

    nodeids = cache_utils.read_flaky_tests()
    assert nodeids == []  # should gracefully treat as empty


def test_read_flaky_tests_valid_schema(monkeypatch, tmp_path):
    ci_dir = tmp_path / "ci"
    ci_dir.mkdir(parents=True, exist_ok=True)
    flaky_file = ci_dir / "flaky_tests.json"
    flaky_file.write_text(
        json.dumps({"nodeids": ["pkg/test_a.py::test_one", "pkg/test_b.py::test_two"]}),
        encoding="utf-8",
    )

    monkeypatch.setattr(cache_utils, "FLAKY_FILE", flaky_file, raising=False)

    nodeids = cache_utils.read_flaky_tests()
    assert nodeids == [
        "pkg/test_a.py::test_one",
        "pkg/test_b.py::test_two",
    ]


def test_read_flaky_tests_handles_string(monkeypatch, tmp_path):
    ci_dir = tmp_path / "ci"
    ci_dir.mkdir(parents=True, exist_ok=True)
    flaky_file = ci_dir / "flaky_tests.json"
    flaky_file.write_text(
        json.dumps({"nodeids": "pkg/test_c.py::test_three"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(cache_utils, "FLAKY_FILE", flaky_file, raising=False)

    nodeids = cache_utils.read_flaky_tests()
    assert nodeids == ["pkg/test_c.py::test_three"]


def test_read_flaky_tests_ignores_bad_schema(monkeypatch, tmp_path: Path, capsys):
    ci_dir = tmp_path / "ci"
    ci_dir.mkdir(parents=True, exist_ok=True)
    flaky_file = ci_dir / "flaky_tests.json"
    flaky_file.write_text(
        json.dumps({"nodeids": {"weird": "object"}}),
        encoding="utf-8",
    )

    monkeypatch.setattr(cache_utils, "FLAKY_FILE", flaky_file, raising=False)

    nodeids = cache_utils.read_flaky_tests()
    captured = capsys.readouterr()

    assert nodeids == []
    assert "unexpected flaky file schema" in captured.out
