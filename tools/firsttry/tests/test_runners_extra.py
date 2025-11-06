import types

from firsttry import runners


def test_coverage_gate_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    res = runners.coverage_gate(80)
    assert res.ok is False
    assert "no coverage.xml" in res.stdout


def test_parse_cobertura_no_line_rate(tmp_path, monkeypatch):
    xml = """<?xml version=\"1.0\" ?><coverage></coverage>"""
    p = tmp_path / "coverage.xml"
    p.write_text(xml, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    rate = runners.parse_cobertura_line_rate()
    assert rate is None


def test_run_black_check_failure(monkeypatch):
    def fake_run(args, stdout, stderr, text, cwd=None):
        return types.SimpleNamespace(returncode=1, stdout="", stderr="boom")

    # Patch subprocess.run so `_exec` will pick up our fake regardless of
    # whether the module bound it at import time.
    monkeypatch.setattr("subprocess.run", fake_run)
    res = runners.run_black_check(["."])
    assert res.ok is False
    assert res.name == "black"


def test_run_pytest_kexpr_builds_k(monkeypatch):
    captured = {}

    def fake_run(args, stdout, stderr, text, cwd=None):
        captured["args"] = args
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    _ = runners.run_pytest_kexpr("lint", base_args=("-q",))
    assert "-k" in captured["args"] and "lint" in captured["args"]
