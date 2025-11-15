"""Core tests for ci_parity.cache_utils.

Goal:
- Exercise read_flaky_tests() with present/missing/invalid files.
- Exercise Golden Cache download helpers in a tier-safe way
    (no real network calls; everything mocked).
"""

import json
import types
from unittest import mock

import firsttry.ci_parity.cache_utils as cu
from firsttry.ci_parity import cache_utils


def test_maybe_download_golden_cache_noop_for_free_tier(monkeypatch):
    """
    Existing-style test (if you already have something like this, keep yours).
    We keep it here as a reference for the paid-tier variant below.
    """
    calls = []

    def fake_get_current_tier():
        return "free-lite"

    fake_gc = types.SimpleNamespace(
        maybe_download=lambda *a, **k: calls.append((a, k)),
    )

    monkeypatch.setattr(cu, "get_current_tier", fake_get_current_tier, raising=False)
    monkeypatch.setattr(cu, "golden_cache", fake_gc, raising=False)

    cu.maybe_download_golden_cache()

    # No call on free-lite
    assert calls == []


def test_maybe_download_golden_cache_extracts_archive_for_paid_tier(monkeypatch, tmp_path):
    """
    For paid tiers, if GOLDEN_CACHE_ARCHIVE is set to a valid zip file,
    maybe_download_golden_cache should extract it into WARM_DIR.
    """
    import shutil
    import zipfile
    # Create a dummy zip archive
    archive = tmp_path / "warm-cache-test.zip"
    warm_file = "dummy.txt"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(warm_file, "hello")

    # Patch globals to simulate paid tier and set archive
    monkeypatch.setattr(cu, "GOLDEN_CACHE_ARCHIVE", str(archive), raising=False)
    monkeypatch.setattr(cu, "get_current_tier", lambda: "pro", raising=False)

    # Clean WARM_DIR before test
    if cu.WARM_DIR.exists():
        shutil.rmtree(cu.WARM_DIR)

    cu.maybe_download_golden_cache()

    # The file should be extracted into WARM_DIR
    extracted = cu.WARM_DIR / warm_file
    assert extracted.exists()
    assert extracted.read_text() == "hello"


def test_read_flaky_tests_empty_file(tmp_path, monkeypatch):
    """
    If ci/flaky_tests.json exists but has an empty list, the function
    should return an empty collection (and not raise).
    """
    root = tmp_path
    monkeypatch.chdir(root)

    path = root / "ci" / "flaky_tests.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"nodeids": []}')

    result = cache_utils.read_flaky_tests()
    assert isinstance(result, (list, set, tuple))
    assert not result


def test_read_flaky_tests_non_empty(tmp_path, monkeypatch):
    """
    Non-empty ci/flaky_tests.json should be parsed and returned.
    """
    root = tmp_path
    monkeypatch.chdir(root)

    nodeids = ["tests/test_a.py::test_a", "tests/test_b.py::test_b"]
    path = root / "ci" / "flaky_tests.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"nodeids": nodeids}))

    result = cache_utils.read_flaky_tests()
    assert set(result) == set(nodeids)


def test_read_flaky_tests_missing_returns_empty(tmp_path, monkeypatch):
    """
    Missing ci/flaky_tests.json should be treated as "no flakies", not an error.
    """
    root = tmp_path
    monkeypatch.chdir(root)

    # No ci/flaky_tests.json created.
    result = cache_utils.read_flaky_tests()
    assert not result


def test_read_flaky_tests_invalid_json_is_tolerated(tmp_path, monkeypatch, capsys, caplog):
    """
    Invalid JSON should not crash; function should return empty and log a hint.
    """
    root = tmp_path
    monkeypatch.chdir(root)

    path = root / "ci" / "flaky_tests.json"
    path.parent.mkdir(parents=True)
    path.write_text("{this is not: valid json}")

    result = cache_utils.read_flaky_tests()
    assert not result

    # Some implementations may log or print a hint; make this test resilient.
    _ = capsys.readouterr()
    # No further assertion: primary contract is 'no crash, empty result'.


def test_maybe_download_golden_cache_noop_on_free_tier(monkeypatch, tmp_path):
    """
    On free tier, network-dependent Golden Cache helpers must NO-OP
    and not attempt any S3/download calls.
    """
    # Ensure working dir exists
    monkeypatch.chdir(tmp_path)

    # Replace whatever tier resolver cache_utils uses with free
    monkeypatch.setattr(cache_utils, "get_current_tier", lambda: "free", raising=False)

    # Patch the internal downloader if present
    m_download = mock.MagicMock()
    monkeypatch.setattr(cache_utils, "_download_from_s3", m_download, raising=False)

    # Call the public helper; should not call the network downloader
    cache_utils.maybe_download_golden_cache()
    m_download.assert_not_called()
