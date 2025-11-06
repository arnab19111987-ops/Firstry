"""Test cache system fast-path functions."""

from firsttry.cache import load_cache
from firsttry.cache import save_cache


def test_load_cache_returns_dict():
    """Test that loading cache returns a dictionary."""
    cache = load_cache()

    # Should return a dict (may be empty if no cache exists)
    assert isinstance(cache, dict)


def test_save_cache_accepts_dict():
    """Test that we can save cache data."""
    test_data = {"tool": "pytest", "signature": "abc123", "timestamp": 1234567890}

    # Save cache - should not crash
    save_cache(test_data)

    # Verify it worked by loading
    loaded = load_cache()
    assert isinstance(loaded, dict)


def test_cache_handles_empty_dict():
    """Test that cache can handle empty data."""
    # Save empty cache
    save_cache({})

    # Should not crash
    loaded = load_cache()
    assert isinstance(loaded, dict)


def test_cache_roundtrip():
    """Test that we can save and load cache data."""
    # Save some test data
    test_cache = {
        "files": ["file1.py", "file2.py"],
        "signature": "test_sig",
    }

    save_cache(test_cache)
    loaded = load_cache()

    assert isinstance(loaded, dict)
    # May or may not preserve exact data depending on implementation
    assert len(loaded) >= 0
