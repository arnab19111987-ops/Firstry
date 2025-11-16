from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("firsttry.ft_fastpath")

import firsttry.ft_fastpath as native
from firsttry.twin.hashers import hash_file


def test_ft_fastpath_hash_matches_python(tmp_path: Path):
    p = tmp_path / "sample.txt"
    p.write_text("hello ft_fastpath", encoding="utf-8")

    py_digest = hash_file(p)
    native_pairs = native.hash_files_parallel([str(p)])
    # native.hash_files_parallel returns list of (path, digest) in our shim
    assert isinstance(native_pairs, list)
    assert native_pairs, "native hash_files_parallel returned empty"
    native_digest = native_pairs[0][1]

    assert py_digest == native_digest
