import pytest
from firsttry.gates import run_gate, build_gate_summary, print_gate_human_summary


def test_gate_dev_prints_summary(capsys):
    gr, ok = run_gate("pre-commit")
    summary = build_gate_summary("dev", gr)
    print_gate_human_summary(summary)
    out = capsys.readouterr().out
    assert "Gate: dev" in out
    assert "Checked:" in out
    assert "Skipped:" in out
    assert "Unknown:" in out
    assert "Result:" in out


def test_gate_release_includes_skipped_cloud_only_jobs(capsys):
    gr, ok = run_gate("pre-push")
    summary = build_gate_summary("release", gr)
    print_gate_human_summary(summary)
    out = capsys.readouterr().out
    assert "Gate: release" in out
    assert "Skipped:" in out
    # At least one skipped job (e.g. docker_smoke)
    assert any("docker_smoke" in line for line in out.splitlines())
    assert "Result:" in out
