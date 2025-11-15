"""
Tests for divergence-monitor logic that enforces exit 99.
"""

from types import SimpleNamespace

import pytest

from firsttry.ci_parity import monitor


def test_divergence_exit_99_when_warm_pass_full_fail(capsys, monkeypatch):
    """
    When warm=PASS and full=FAIL, the monitor should exit 99 and print a
    divergence message.
    """

    def fake_load_report(warm_junit, full_junit):
        return SimpleNamespace(
            warm_pass=True,
            full_pass=False,
            warm_fail_ids=set(),
            full_fail_ids={"tests/test_x.py::test_fail"},
        )

    monkeypatch.setattr(monitor, "load_report", fake_load_report)

    with pytest.raises(SystemExit) as exc:
        monitor.main(["prog"])  # argv passed; load_report will be used

    assert exc.value.code == 99
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "DIVERGENCE" in out.upper()


def test_divergence_exit_zero_when_both_pass(capsys, monkeypatch):
    """
    Warm and full both PASS → exit code 0, no divergence warning.
    """

    def fake_load_report(warm_junit, full_junit):
        return SimpleNamespace(
            warm_pass=True,
            full_pass=True,
            warm_fail_ids=set(),
            full_fail_ids=set(),
        )

    monkeypatch.setattr(monitor, "load_report", fake_load_report)

    with pytest.raises(SystemExit) as exc:
        monitor.main(["prog"])  # should sys.exit(0)

    assert exc.value.code == 0
    captured = capsys.readouterr()
    out = captured.out + captured.err
    assert "DIVERGENCE" not in out.upper()
