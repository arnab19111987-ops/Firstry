import subprocess

from firsttry.gates.go_tests import GoTestGate


def test_go_test_gate_skips_when_not_installed(monkeypatch, tmp_path):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(subprocess, "run", fake_run)

    gate = GoTestGate()
    res = gate.run(tmp_path)
    assert res.ok is True
    assert res.skipped is True
    assert "not installed" in res.reason
