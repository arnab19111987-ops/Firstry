from __future__ import annotations

from pathlib import Path

from firsttry.twin.hashers import hash_bytes
from firsttry.twin.hashers import hash_file
from firsttry.twin.hashers import hash_files


def test_hash_bytes_is_deterministic():
    a = b"hello world"
    b = b"hello world"
    c = b"hello-world"

    ha1 = hash_bytes(a)
    ha2 = hash_bytes(b)
    hc = hash_bytes(c)

    assert ha1 == ha2
    assert ha1 != hc
    assert len(ha1) == len(hc)  # hex string length stable


def test_hash_file_matches_hash_bytes(tmp_path: Path):
    content = b"some content to hash"
    p = tmp_path / "file.txt"
    p.write_bytes(content)

    hf = hash_file(p)
    hb = hash_bytes(content)

    assert hf == hb


def test_hash_files_is_order_independent(tmp_path: Path):
    f1 = tmp_path / "a.py"
    f2 = tmp_path / "b.py"

    f1.write_text("print('a')\n", encoding="utf-8")
    f2.write_text("print('b')\n", encoding="utf-8")

    digest1 = hash_files([f1, f2])
    digest2 = hash_files([f2, f1])

    assert digest1 == digest2
    assert isinstance(digest1, str)
    assert len(digest1) > 0
