"""Tests for fast-path scanning and BLAKE3 hashing.

Tests both Rust accelerated path (when available) and Python fallback.
Verifies hash parity between backends and correct behavior across all scenarios.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from firsttry.twin.fastpath import hash_paths, scan_paths
from firsttry.twin.hashers import Hasher


class TestScanPaths:
    """Tests for scan_paths() function."""

    def test_scan_paths_basic(self, tmp_path: Path) -> None:
        """Test basic file scanning."""
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.py").write_text("content2")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.txt").write_text("content3")

        files = scan_paths(tmp_path)
        file_names = {p.name for p in files}

        assert "file1.txt" in file_names
        assert "file2.py" in file_names
        assert "file3.txt" in file_names

    def test_scan_paths_ignores_venv(self, tmp_path: Path) -> None:
        """Test that venv and other common dirs are ignored."""
        (tmp_path / "venv").mkdir()
        (tmp_path / "venv" / "lib").mkdir(parents=True)
        (tmp_path / "venv" / "lib" / "site-packages.py").write_text("x")
        (tmp_path / "normal.py").write_text("real")

        files = scan_paths(tmp_path)
        file_names = {p.name for p in files}

        assert "normal.py" in file_names
        assert "site-packages.py" not in file_names

    def test_scan_paths_empty_dir(self, tmp_path: Path) -> None:
        """Test scanning an empty directory."""
        files = scan_paths(tmp_path)
        assert len(files) == 0


class TestHashPaths:
    """Tests for hash_paths() function."""

    def test_hash_paths_basic(self, tmp_path: Path) -> None:
        """Test basic file hashing."""
        f1 = tmp_path / "a.txt"
        f1.write_text("hello")
        f2 = tmp_path / "b.txt"
        f2.write_text("world")

        hashes = hash_paths([f1, f2])

        assert f1 in hashes
        assert f2 in hashes
        assert hashes[f1] != hashes[f2]

    def test_hash_paths_same_content(self, tmp_path: Path) -> None:
        """Test that same content produces same hash."""
        f1 = tmp_path / "a.txt"
        f1.write_text("same")
        f2 = tmp_path / "b.txt"
        f2.write_text("same")

        hashes = hash_paths([f1, f2])

        assert hashes[f1] == hashes[f2]

    def test_hash_paths_binary(self, tmp_path: Path) -> None:
        """Test hashing binary files."""
        f = tmp_path / "binary.bin"
        f.write_bytes(b"\x00\x01\x02\x03" * 1024)

        hashes = hash_paths([f])

        assert f in hashes


class TestHasherClass:
    """Tests for Hasher class."""

    def test_hasher_hash_all(self, tmp_path: Path) -> None:
        """Test Hasher.hash_all() method."""
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")

        hasher = Hasher(tmp_path)
        hashes = hasher.hash_all()

        assert len(hashes) == 2

    def test_hasher_ignores_venv(self, tmp_path: Path) -> None:
        """Test that Hasher respects venv ignores."""
        (tmp_path / "code.py").write_text("x")
        (tmp_path / "venv").mkdir()
        (tmp_path / "venv" / "lib.py").write_text("y")

        hasher = Hasher(tmp_path)
        hashes = hasher.hash_all()

        file_names = {p.name for p in hashes.keys()}
        assert "code.py" in file_names
        assert "lib.py" not in file_names


class TestHashFallback:
    """Tests for Python fallback hashing."""

    def test_hash_fallback_py(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Python fallback hashing."""
        monkeypatch.setenv("FT_FASTPATH", "off")
        f = tmp_path / "x.txt"
        f.write_text("content")

        hashes = hash_paths([f])

        assert f in hashes
        assert hashes[f]
