from firsttry.cache import load_cache
from firsttry.cache import save_cache
from firsttry.cache import should_skip_gate
from firsttry.cache import update_gate_cache


def test_load_cache_when_missing(tmp_path, monkeypatch):
    # Test that load_cache returns empty structure when cache doesn't exist
    cache_file = tmp_path / "test_cache.json"
    # Import the package to get access to the internal _legacy_cache module
    import firsttry.cache as cache_pkg

    if cache_pkg._legacy_cache is not None:
        monkeypatch.setattr(cache_pkg._legacy_cache, "CACHE_FILE", cache_file)
    data = load_cache()
    assert data == {"repos": {}}


def test_save_and_load_cache(tmp_path, monkeypatch):
    # Test save and load cycle
    cache_file = tmp_path / "test_cache.json"
    # Patch the legacy cache module
    import firsttry.cache as cache_pkg

    if cache_pkg._legacy_cache is not None:
        monkeypatch.setattr(cache_pkg._legacy_cache, "CACHE_FILE", cache_file)

    data = {"hello": "world", "repos": {}}
    save_cache(data)
    loaded = load_cache()
    assert loaded == data
    assert "repos" in loaded


def test_should_skip_gate_with_changed_files():
    # prepare cache
    cache = {}
    update_gate_cache(cache, "python:ruff", ["pyproject.toml"])
    # if changed file is in watched → should NOT skip
    should = should_skip_gate(cache, "python:ruff", ["pyproject.toml"])
    assert should is False
    # if changed file is different → should skip
    should2 = should_skip_gate(cache, "python:ruff", ["README.md"])
    assert should2 is True
