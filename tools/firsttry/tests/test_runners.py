import types
from pathlib import Path

from firsttry import runners


def test_parse_cobertura_line_rate(tmp_path: Path, monkeypatch):
    xml = """<?xml version="1.0" ?>
<coverage line-rate="0.8734" branch-rate="0.5" version="1.9" timestamp="0"></coverage>"""
    p = tmp_path / "coverage.xml"
    p.write_text(xml, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    rate = runners.parse_cobertura_line_rate()
    assert rate is not None
    assert abs(rate - 87.34) < 0.01


def test_coverage_gate_ok(tmp_path: Path, monkeypatch):
    xml = """<?xml version="1.0" ?>
<coverage line-rate="0.95"></coverage>"""
    (tmp_path / "coverage.xml").write_text(xml, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    res = runners.coverage_gate(90)
    assert res.ok
    assert "95.00%" in res.stdout


def test_exec_wrapper_monkeypatch(monkeypatch):
    def fake_run(args, stdout, stderr, text, cwd=None):
        ns = types.SimpleNamespace(returncode=0, stdout="ok", stderr="")
        return ns

    # Patch the subprocess.run entrypoint so `_exec` uses the stub regardless
    # of import-time binding differences.
    monkeypatch.setattr("subprocess.run", fake_run)
    r = runners.run_ruff(["tools/firsttry/firsttry"])
    assert r.ok and r.name == "ruff"
