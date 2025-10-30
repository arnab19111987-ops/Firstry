from firsttry.cache import (
    load_cache,
    save_cache,
    should_skip_gate,
    update_gate_cache,
)


def test_load_cache_when_missing(tmp_path):
    data = load_cache(tmp_path)
    assert data == {}


def test_save_and_load_cache(tmp_path):
    data = {"hello": "world"}
    save_cache(tmp_path, data)
    loaded = load_cache(tmp_path)
    assert loaded["hello"] == "world"
    assert "updated_at" in loaded


def test_should_skip_gate_with_changed_files(tmp_path):
    # prepare cache
    cache = {}
    update_gate_cache(cache, "python:ruff", ["pyproject.toml"])
    # if changed file is in watched → should NOT skip
    should = should_skip_gate(cache, "python:ruff", ["pyproject.toml"])
    assert should is False
    # if changed file is different → should skip
    should2 = should_skip_gate(cache, "python:ruff", ["README.md"])
    assert should2 is True
