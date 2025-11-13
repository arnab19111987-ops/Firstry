import json

from firsttry.ci_parity.cache_utils import load_flaky_nodeids


def test_flaky_file_absent_ok(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert load_flaky_nodeids() == []


def test_flaky_file_present(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ci").mkdir()
    (tmp_path / "ci/flaky_tests.json").write_text(json.dumps(["a::b", "c::d"]))
    assert load_flaky_nodeids() == ["a::b", "c::d"]
