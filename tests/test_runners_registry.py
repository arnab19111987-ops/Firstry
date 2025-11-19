from firsttry.runners import RUNNERS


def test_runners_has_custom_runner() -> None:
    """Ensure RUNNERS always exposes a 'custom' runner and it's runnable."""
    assert "custom" in RUNNERS, "RUNNERS must include 'custom'"
    cr = RUNNERS.get("custom")
    assert cr is not None
    assert hasattr(cr, "run") or callable(cr), "custom runner must be runnable"


def test_runners_have_core_tools() -> None:
    """Ensure core tool runners are present and have a run/prereq interface."""
    core = ["ruff", "mypy", "pytest"]
    for c in core:
        assert c in RUNNERS, f"{c} should be registered in RUNNERS"
        obj = RUNNERS[c]
        assert obj is not None
        assert hasattr(obj, "run") or callable(obj), f"{c} runner must be callable or have a run method"
