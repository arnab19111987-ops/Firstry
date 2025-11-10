"""Tests for repository state fingerprinting (repo_fingerprint).

Verifies that:
1. Fingerprints are stable for unchanged repos
2. Fingerprints change when files are modified
3. Volatile paths (.firsttry, __pycache__) don't affect fingerprints
4. Fingerprint format is correct (hex, proper length)
"""

from pathlib import Path

import pytest

from firsttry.runner import state


def write(p: Path, rel: str, txt: str):
    """Helper to write a file relative to a base path."""
    (p / rel).parent.mkdir(parents=True, exist_ok=True)
    (p / rel).write_text(txt, encoding="utf-8")


def test_fingerprint_stable(tmp_path: Path, monkeypatch):
    """Test that fingerprint is stable for unchanged repo."""
    # Change to temp repo
    monkeypatch.chdir(tmp_path)

    # Write some source files
    write(tmp_path, "src/a.py", "print('a')\n")
    write(tmp_path, "src/sub/b.py", "x=1\n")
    write(tmp_path, "tests/test_a.py", "def test_basic():\n    assert True\n")

    # Compute fingerprint twice
    f1 = state.repo_fingerprint({"test": "1"})
    f2 = state.repo_fingerprint({"test": "1"})

    # Should be identical
    assert f1 == f2, "Fingerprints should be stable"
    assert len(f1) in (32, 64, 128), f"Fingerprint length unexpected: {len(f1)}"
    # BLAKE2b-128 produces 32 hex chars (16 bytes * 2)
    assert len(f1) == 32, "BLAKE2b-16 should produce 32-char hex"


def test_fingerprint_changes_on_file_update(tmp_path: Path, monkeypatch):
    """Test that fingerprint changes when a file is modified."""
    monkeypatch.chdir(tmp_path)

    # Initial files
    write(tmp_path, "src/a.py", "print('a')\n")
    write(tmp_path, "src/b.py", "x = 1\n")

    f1 = state.repo_fingerprint({"test": "1"})

    # Modify one file
    write(tmp_path, "src/a.py", "print('a2')\n")
    f2 = state.repo_fingerprint({"test": "1"})

    # Fingerprints should differ
    assert f1 != f2, "Fingerprint should change when file content changes"


def test_fingerprint_changes_on_file_add(tmp_path: Path, monkeypatch):
    """Test that fingerprint changes when a new file is added."""
    monkeypatch.chdir(tmp_path)

    write(tmp_path, "src/a.py", "print('a')\n")
    f1 = state.repo_fingerprint({"test": "1"})

    # Add new file
    write(tmp_path, "src/new_module.py", "def func():\n    pass\n")
    f2 = state.repo_fingerprint({"test": "1"})

    assert f1 != f2, "Fingerprint should change when new file is added"


def test_fingerprint_ignores_volatile_paths(tmp_path: Path, monkeypatch):
    """Test that volatile paths don't affect fingerprint."""
    monkeypatch.chdir(tmp_path)

    write(tmp_path, "src/code.py", "print(1)\n")
    f1 = state.repo_fingerprint({"test": "1"})

    # Add volatile paths (not in INCLUDE_GLOBS by default)
    write(tmp_path, ".firsttry/report.json", '{"noise":true}')
    write(tmp_path, "__pycache__/code.cpython-312.pyc", "x")
    write(tmp_path, ".pytest_cache/pytest_cache.json", "cache")
    write(tmp_path, "build/artifact.whl", "binary")

    f2 = state.repo_fingerprint({"test": "1"})

    # Fingerprints should be identical (volatile paths ignored)
    assert f1 == f2, "Volatile paths (.firsttry, __pycache__, etc.) must not affect fingerprint"


def test_fingerprint_includes_config_files(tmp_path: Path, monkeypatch):
    """Test that config files are included in fingerprint."""
    monkeypatch.chdir(tmp_path)

    write(tmp_path, "src/a.py", "x=1\n")
    f1 = state.repo_fingerprint({"test": "1"})

    # Add config file (in INCLUDE_GLOBS)
    write(tmp_path, "pyproject.toml", '[project]\nname="test"\n')
    f2 = state.repo_fingerprint({"test": "1"})

    # Should differ because config file added
    assert f1 != f2, "Config files should be included in fingerprint"


def test_fingerprint_includes_test_files(tmp_path: Path, monkeypatch):
    """Test that test files are included in fingerprint."""
    monkeypatch.chdir(tmp_path)

    write(tmp_path, "src/code.py", "def func():\n    pass\n")
    f1 = state.repo_fingerprint({"test": "1"})

    # Add test file
    write(tmp_path, "tests/test_code.py", "def test_func():\n    assert True\n")
    f2 = state.repo_fingerprint({"test": "1"})

    # Should differ
    assert f1 != f2, "Test files should be included in fingerprint"


def test_fingerprint_includes_salt_metadata(tmp_path: Path, monkeypatch):
    """Test that extra metadata affects fingerprint."""
    monkeypatch.chdir(tmp_path)

    write(tmp_path, "src/a.py", "x=1\n")

    # Same extra metadata
    f1 = state.repo_fingerprint({"version": "1.0", "env": "prod"})
    f2 = state.repo_fingerprint({"version": "1.0", "env": "prod"})
    assert f1 == f2

    # Different metadata
    f3 = state.repo_fingerprint({"version": "2.0", "env": "prod"})
    assert f1 != f3, "Different metadata should produce different fingerprint"


def test_fingerprint_is_hex(tmp_path: Path, monkeypatch):
    """Test that fingerprint is valid hex."""
    monkeypatch.chdir(tmp_path)
    write(tmp_path, "src/a.py", "x=1\n")

    fp = state.repo_fingerprint({"test": "1"})

    # Should be valid hex
    try:
        int(fp, 16)
    except ValueError:
        pytest.fail(f"Fingerprint is not valid hex: {fp}")


def test_load_and_save_last_green(tmp_path: Path, monkeypatch):
    """Test load/save of last green run state."""
    monkeypatch.chdir(tmp_path)

    # Initially nothing
    last = state.load_last_green()
    assert last is None

    # Save some state
    data = {"fingerprint": "abc123def456", "report": {"status": "ok", "tasks": 5, "passed": 5}}
    state.save_last_green(data)

    # Load it back
    loaded = state.load_last_green()
    assert loaded is not None
    assert loaded["fingerprint"] == "abc123def456"
    assert loaded["report"]["status"] == "ok"


def test_fingerprint_path_ordering(tmp_path: Path, monkeypatch):
    """Test that fingerprint is independent of file creation order."""
    monkeypatch.chdir(tmp_path)

    # Create files in one order
    write(tmp_path, "src/a.py", "a=1\n")
    write(tmp_path, "src/b.py", "b=2\n")
    write(tmp_path, "src/c.py", "c=3\n")
    f1 = state.repo_fingerprint({"test": "1"})

    # Clear and recreate in different order

    for f in tmp_path.glob("src/*.py"):
        f.unlink()

    write(tmp_path, "src/c.py", "c=3\n")
    write(tmp_path, "src/a.py", "a=1\n")
    write(tmp_path, "src/b.py", "b=2\n")
    f2 = state.repo_fingerprint({"test": "1"})

    # Fingerprints should match (deterministic, sorted)
    assert f1 == f2, "Fingerprints should be deterministic regardless of creation order"
