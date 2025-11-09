import importlib
import os

import pytest


def test_cache_utils_path_and_hash(tmp_path, monkeypatch):
    m = importlib.import_module("firsttry.cache_utils")

    norm = getattr(m, "normalize_path", None) or getattr(m, "norm_path", None)
    mkhash = getattr(m, "file_hash", None) or getattr(m, "hash_file", None)
    if not callable(norm) and not callable(mkhash):
        pytest.skip("cache_utils lacks normalize_path/hash helpers in this revision.")

    # Create a tiny file
    p = tmp_path / "dir" / "file.txt"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("hello\n", encoding="utf-8")

    # normalize_path
    if callable(norm):
        np = norm(str(p))
        assert isinstance(np, str)
        # most implementations should end without trailing slash for files
        assert os.path.basename(np).startswith("file")

    # file_hash
    if callable(mkhash):
        hv = mkhash(str(p))
        assert isinstance(hv, str)
        # sanity: should match sha256/xxhash/blake3 style hex length (just check hex-like)
        assert all(c in "0123456789abcdef" for c in hv.lower())
