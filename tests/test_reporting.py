from firsttry.reporting import print_summary
from firsttry.gates.base import GateResult


def test_print_summary(capsys):
    results = [
        GateResult(gate_id="python:ruff", ok=True),
        GateResult(gate_id="python:mypy", ok=False, output="error"),
        GateResult(gate_id="security:bandit", ok=True, skipped=True, reason="not installed"),
    ]
    print_summary(results)
    out = capsys.readouterr().out
    assert "FirstTry Summary" in out
    assert "python:ruff" in out
    assert "python:mypy" in out
    assert "Failed: 1" in out
