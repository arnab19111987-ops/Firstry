"""
Tests for core summary report functions.

Goal:
- Exercise the “summarize checks into buckets/verdict” logic.
- No file IO: use in-memory structures where possible.
"""

from firsttry.reports import summary as summary_mod


def test_compute_overall_verdict_ready_when_all_pass(capsys, monkeypatch):
    checks = {
        "ruff": {"passed": True, "summary": "ok"},
        "mypy": {"passed": True, "summary": "ok"},
    }
    context = {"machine": 2, "files": 10, "tests": 2}
    # render_summary_legacy prints overall PASS/FAILED; capture and assert
    # Ensure the tier used by the renderer maps to a known key in TIER_CHECKS
    monkeypatch.setattr(summary_mod, "get_tier", lambda: "free-lite")
    # Ensure legacy fallback key 'free' exists to avoid KeyError in renderer
    monkeypatch.setitem(summary_mod.TIER_CHECKS, "free", summary_mod.TIER_CHECKS.get("free-lite"))
    summary_mod.render_summary_legacy(checks, context)
    out = capsys.readouterr().out
    assert "PASSED" in out or "✅ PASSED" in out


def test_compute_overall_verdict_partial_when_any_partial_or_fail(capsys, monkeypatch):
    checks = {
        "ruff": {"passed": True, "summary": "ok"},
        "mypy": {"passed": False, "summary": "type errors"},
    }
    context = {"machine": 2, "files": 10, "tests": 2}
    # Use free-strict so mypy is included in allowed checks for this test
    monkeypatch.setattr(summary_mod, "get_tier", lambda: "free-strict")
    # Ensure legacy fallback key 'free' exists to avoid KeyError in renderer
    monkeypatch.setitem(summary_mod.TIER_CHECKS, "free", summary_mod.TIER_CHECKS.get("free-lite"))
    summary_mod.render_summary_legacy(checks, context)
    out = capsys.readouterr().out
    assert "FAILED" in out or "❌ FAILED" in out
