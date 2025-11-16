from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Optional

import pytest

try:
    ff_mod: Optional[ModuleType] = import_module("firsttry.ft_fastpath")
except Exception:
    ff_mod = None

import blake3


@pytest.mark.skipif(ff_mod is None, reason="Rust fastpath not present")
def test_hashes_match_python_fallback(tmp_path: Path):
    p = tmp_path / "f.txt"
    p.write_text("abc")
    assert ff_mod is not None
    rust = dict(ff_mod.hash_files_parallel([str(p)]))
    py = blake3.blake3(p.read_bytes()).hexdigest()
    assert rust[str(p)] == py
