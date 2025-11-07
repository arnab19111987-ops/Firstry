"""Tests for fast-path scanning."""

from pathlib import Path

from firsttry.twin.fastpath_scan import scan_paths


def test_scan_paths_basic(tmp_path: Path, monkeypatch):
    """Test basic scanning with Python fallback."""
    monkeypatch.setenv("FT_FASTPATH", "off")  # Force Python fallback for this test

    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.py").write_text("b")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "ignored.txt").write_text("x")

    files = set(scan_paths(tmp_path))
    assert (tmp_path / "a.txt") in files
    assert (tmp_path / "b.py") in files
    # .git content should be ignored by both rust and python paths
    assert (tmp_path / ".git" / "ignored.txt") not in files


def test_scan_paths_ignores_venv(tmp_path: Path, monkeypatch):
    """Test that venv directory is ignored."""
    monkeypatch.setenv("FT_FASTPATH", "off")  # Force Python fallback

    (tmp_path / "src.py").write_text("code")
    (tmp_path / "venv").mkdir()
    (tmp_path / "venv" / "pyvenv.cfg").write_text("home = /usr")

    files = set(scan_paths(tmp_path))
    assert (tmp_path / "src.py") in files
    assert (tmp_path / "venv" / "pyvenv.cfg") not in files


def test_scan_paths_ignores_pyc(tmp_path: Path, monkeypatch):
    """Test that .pyc files are ignored."""
    monkeypatch.setenv("FT_FASTPATH", "off")  # Force Python fallback

    (tmp_path / "module.py").write_text("code")
    (tmp_path / "module.pyc").write_text("bytecode")

    files = set(scan_paths(tmp_path))
    assert (tmp_path / "module.py") in files
    assert (tmp_path / "module.pyc") not in files


def test_scan_paths_nested_dirs(tmp_path: Path, monkeypatch):
    """Test scanning nested directories."""
    monkeypatch.setenv("FT_FASTPATH", "off")  # Force Python fallback

    (tmp_path / "dir1").mkdir()
    (tmp_path / "dir1" / "file1.txt").write_text("1")
    (tmp_path / "dir1" / "dir2").mkdir()
    (tmp_path / "dir1" / "dir2" / "file2.txt").write_text("2")

    files = set(scan_paths(tmp_path))
    assert (tmp_path / "dir1" / "file1.txt") in files
    assert (tmp_path / "dir1" / "dir2" / "file2.txt") in files


def test_scan_paths_empty_dir(tmp_path: Path, monkeypatch):
    """Test scanning empty directory."""
    monkeypatch.setenv("FT_FASTPATH", "off")  # Force Python fallback

    files = scan_paths(tmp_path)
    assert len(files) == 0


def test_scan_paths_with_threads(tmp_path: Path, monkeypatch):
    """Test scanning with explicit thread count."""
    monkeypatch.setenv("FT_FASTPATH", "off")  # Force Python fallback

    (tmp_path / "file1.txt").write_text("1")
    (tmp_path / "file2.txt").write_text("2")

    # Test with explicit threads (Python fallback ignores this but should not error)
    files = scan_paths(tmp_path, threads=4)
    assert len(files) == 2
