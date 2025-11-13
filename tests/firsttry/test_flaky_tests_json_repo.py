import json
from pathlib import Path

from firsttry.ci_parity.cache_utils import read_flaky_tests


def test_repo_flaky_tests_json_is_valid_and_schema_ok() -> None:
    """The committed ci/flaky_tests.json must be valid JSON with the expected schema.

    This guards against accidental edits that append junk and break parsing.
    """
    path = Path("ci/flaky_tests.json")
    assert path.is_file(), "ci/flaky_tests.json must exist in the repo"

    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)  # will raise if malformed

    assert isinstance(data, dict), "flaky_tests.json must be a JSON object"
    assert "nodeids" in data, "flaky_tests.json must contain a 'nodeids' key"
    assert isinstance(
        data["nodeids"], list
    ), "'nodeids' must be a JSON list (even if empty)"

    # And read_flaky_tests() should see the same values
    nodeids = read_flaky_tests()
    assert isinstance(nodeids, list)
    # Committed file is expected to be empty by default
    assert nodeids == []


def test_flaky_tests_json_future_edits_are_detected() -> None:
    """If someone later adds nodeids to the committed file, the test should still pass.

    This test doesn't assert emptiness; it verifies the reader and schema stay stable.
    """
    path = Path("ci/flaky_tests.json")
    data = json.loads(path.read_text(encoding="utf-8"))

    # If nodeids are present in the file, read_flaky_tests must return at least those.
    file_nodeids = data.get("nodeids", [])
    reader_nodeids = read_flaky_tests()

    assert isinstance(reader_nodeids, list)
    for nid in file_nodeids:
        assert nid in reader_nodeids
