from __future__ import annotations

from firsttry.ci_parity.parity_runner import WarmDecision, classify_warm_outcome


def test_classify_warm_outcome_uses_testmon_on_rc0():
    decision = classify_warm_outcome(testmon_rc=0, flaky_nodeids=[])
    assert decision is WarmDecision.USE_TESTMON


def test_classify_warm_outcome_smoke_on_rc5_no_flaky():
    decision = classify_warm_outcome(testmon_rc=5, flaky_nodeids=[])
    assert decision is WarmDecision.RUN_SMOKE


def test_classify_warm_outcome_flaky_only_on_rc5_with_flaky():
    decision = classify_warm_outcome(
        testmon_rc=5,
        flaky_nodeids=["pkg/test_a.py::test_one"],
    )
    assert decision is WarmDecision.RUN_FLAKY_ONLY


def test_classify_warm_outcome_fail_on_other_rc():
    for rc in (1, 2, 3, 4, 10, 99):
        decision = classify_warm_outcome(testmon_rc=rc, flaky_nodeids=[])
        assert decision is WarmDecision.FAIL
