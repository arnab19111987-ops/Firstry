from __future__ import annotations

from types import SimpleNamespace

import pytest

import firsttry.ci_parity.monitor as monitor


def _make_report(warm_pass: bool, full_pass: bool, warm_fail_ids, full_fail_ids):
    return SimpleNamespace(
        warm_pass=warm_pass,
        full_pass=full_pass,
        warm_fail_ids=set(warm_fail_ids),
        full_fail_ids=set(full_fail_ids),
    )


def test_warm_pass_full_fail_exits_99(monkeypatch):
    rep = _make_report(True, False, [], ["t::one"])
    monkeypatch.setattr(monitor, "load_report", lambda *a, **k: rep)

    with pytest.raises(SystemExit) as excinfo:
        monitor.main()

    assert excinfo.value.code == 99


def test_warm_fail_full_pass_flaky_allows_ci(monkeypatch):
    rep = _make_report(False, True, ["t::one"], [])
    monkeypatch.setattr(monitor, "load_report", lambda *a, **k: rep)

    with pytest.raises(SystemExit) as excinfo:
        monitor.main()

    assert excinfo.value.code == 0


def test_both_fail_same_reasons_not_divergent(monkeypatch):
    rep = _make_report(False, False, ["t::one"], ["t::one"])
    monkeypatch.setattr(monitor, "load_report", lambda *a, **k: rep)

    with pytest.raises(SystemExit) as excinfo:
        monitor.main()

    # "normal" failure; exact code may vary (1 or something else),
    # just assert it's not the divergence 99.
    assert excinfo.value.code != 99


def test_both_fail_different_reasons_divergent(monkeypatch):
    rep = _make_report(False, False, ["t::one"], ["t::two"])
    monkeypatch.setattr(monitor, "load_report", lambda *a, **k: rep)

    with pytest.raises(SystemExit) as excinfo:
        monitor.main()

    assert excinfo.value.code == 99
