from __future__ import annotations

from pathlib import Path

from firsttry import self_repair


def test_ensure_dev_support_files_writes_files(tmp_path):
    base = tmp_path / "repo"
    base.mkdir()

    ok = self_repair.ensure_dev_support_files(base_dir=base)
    assert ok is True

    assert (
        base / "requirements-dev.txt"
    ).exists(), "requirements-dev.txt should be created"
    assert (base / "Makefile").exists(), "Makefile should be created"

    # basic content checks
    txt = (base / "requirements-dev.txt").read_text(encoding="utf-8")
    assert "ruff==" in txt


def test_ensure_dev_support_files_fails_on_unwritable(tmp_path):
    base = tmp_path / "readonly_repo"
    base.mkdir()

    # remove write permissions from the directory
    base.chmod(0o555)

    try:
        ok = self_repair.ensure_dev_support_files(base_dir=base)
        # on unwritable dir we expect False
        assert ok is False
    finally:
        # restore permissions so pytest can cleanup the tmp_path
        base.chmod(0o755)


def test_ensure_dev_support_files_wont_overwrite(tmp_path: Path):
    base = tmp_path / "repo"
    base.mkdir()

    # create files beforehand
    (base / "requirements-dev.txt").write_text("existing\n")
    (base / "Makefile").write_text("existing\n")

    ok = self_repair.ensure_dev_support_files(base_dir=base)
    # since files already exist, function should return True and not overwrite
    assert ok is True
    assert (base / "requirements-dev.txt").read_text(encoding="utf-8") == "existing\n"


def test_ensure_dev_support_files_creates_files(tmp_path: Path):
    base = tmp_path / "repo2"
    base.mkdir()
    ok = self_repair.ensure_dev_support_files(base_dir=base)
    assert ok is True
    # Expect the requirements-dev.txt and Makefile were created
    assert (base / "requirements-dev.txt").exists()
    assert (base / "Makefile").exists()
