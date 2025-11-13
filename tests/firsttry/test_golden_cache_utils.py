from __future__ import annotations

import tarfile
from pathlib import Path

import firsttry.ci_parity.cache_utils as cache_utils


def _create_dummy_archive(archive: Path, inner_dir_name: str = "warm_dir"):
    """Create a small tar.gz archive with a dummy warm cache file."""
    tmp_root = archive.parent / "tmp_warm_src"
    warm_dir = tmp_root / inner_dir_name
    warm_dir.mkdir(parents=True, exist_ok=True)
    (warm_dir / "dummy.txt").write_text("cache content", encoding="utf-8")

    with tarfile.open(archive, "w:gz") as tf:
        tf.add(warm_dir, arcname=".firsttry/warm")


def test_maybe_download_golden_cache_applies_archive(tmp_path, monkeypatch):
    artifacts_dir = tmp_path / ".firsttry" / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    archive = artifacts_dir / "golden-cache.tar.gz"
    _create_dummy_archive(archive)

    warm_dir = tmp_path / ".firsttry" / "warm"

    # Redirect the module paths to our temp dirs
    monkeypatch.setattr(cache_utils, "ARTIFACTS_DIR", artifacts_dir, raising=False)
    monkeypatch.setattr(cache_utils, "GOLDEN_CACHE_ARCHIVE", archive, raising=False)
    monkeypatch.setattr(cache_utils, "WARM_DIR", warm_dir, raising=False)

    cache_utils.maybe_download_golden_cache()

    # Expect dummy file to be extracted into WARM_CACHE_DIR
    extracted = warm_dir / "dummy.txt"
    assert extracted.is_file()
    assert extracted.read_text(encoding="utf-8") == "cache content"
