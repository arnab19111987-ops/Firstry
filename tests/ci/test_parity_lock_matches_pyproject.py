import hashlib
import json
from pathlib import Path


def test_parity_lock_pyproject_hash_matches() -> None:
    """Ensure ci/parity.lock.json references the current pyproject.toml hash.

    If this test fails, update `ci/parity.lock.json` with the new hash (see
    ci/README.md or run `sha256sum pyproject.toml`) so CI parity stays in sync.
    """
    repo = Path(__file__).resolve().parents[2]
    lock = repo / "ci" / "parity.lock.json"
    py = repo / "pyproject.toml"

    assert lock.exists(), "ci/parity.lock.json not found"
    assert py.exists(), "pyproject.toml not found"

    data = json.loads(lock.read_text(encoding="utf-8"))

    # Prefer explicit config_hashes entry when present
    cfg_hashes = data.get("config_hashes", {})
    expected = None
    if "pyproject.toml" in cfg_hashes:
        expected = cfg_hashes["pyproject.toml"]
    else:
        # Fallback to project_files.sha256_prefix if present
        pf = data.get("project_files", {}).get("pyproject.toml", {})
        expected = pf.get("sha256_prefix")

    assert expected, "parity lock does not contain pyproject.toml hash/prefix"

    h = hashlib.sha256(py.read_bytes()).hexdigest()

    # If the lock contains a prefix, allow prefix match
    if len(expected) < len(h):
        assert h.startswith(expected), (
            f"pyproject.toml sha256 ({h}) does not match parity lock prefix ({expected}).\n"
            "Run: sha256sum pyproject.toml and update ci/parity.lock.json"
        )
    else:
        assert h == expected, (
            f"pyproject.toml sha256 ({h}) does not match parity lock value ({expected}).\n"
            "Run: sha256sum pyproject.toml and update ci/parity.lock.json"
        )
