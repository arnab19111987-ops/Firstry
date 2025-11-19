from firsttry.runners import RUNNERS


def test_runners_has_custom_runner():
    assert "custom" in RUNNERS, "RUNNERS must include 'custom'"
    # Ensure the custom entry is a runner-like object (has .run or is callable)
    custom = RUNNERS["custom"]
    assert custom is not None, "custom runner must not be None"
    assert hasattr(custom, "run") or callable(custom), "custom runner should have .run or be callable"


def test_runners_has_core_tool_runners():
    for key in ("ruff", "mypy", "pytest"):
        assert key in RUNNERS, f"RUNNERS must include '{key}'"
        runner = RUNNERS[key]
        assert runner is not None, f"runner '{key}' must not be None"
        assert hasattr(runner, "run") or callable(runner), f"runner '{key}' should have .run or be callable"
