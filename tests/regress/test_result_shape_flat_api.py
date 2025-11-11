"""Regression tests to prevent result shape issues."""


def test_normalize_results_flat():
    """Test the _normalize_results_flat function directly."""
    from firsttry.lazy_orchestrator import _normalize_results_flat

    # Test flat list
    flat = [{"name": "tool1", "status": "ok"}]
    result = _normalize_results_flat(flat)
    assert isinstance(result, list)
    assert all(isinstance(r, dict) for r in result)
    assert all("status" in r for r in result)

    # Test nested list
    nested = [
        {"name": "tool1"},
        [{"name": "tool2", "exit_code": 0}, {"name": "tool3", "exit_code": 1}],
    ]
    result = _normalize_results_flat(nested)
    assert len(result) == 3
    assert all("status" in r for r in result)
    assert result[1]["status"] == "ok"  # exit_code 0
    assert result[2]["status"] == "error"  # exit_code 1

    # Test dict without status but with exit_code
    no_status = [{"name": "tool1", "exit_code": 0}]
    result = _normalize_results_flat(no_status)
    assert result[0]["status"] == "ok"

    # Test skipped/noop semantics
    skipped = [{"name": "tool1", "status": "skipped"}]
    result = _normalize_results_flat(skipped)
    assert result[0]["exit_code"] == 0


def test_orchestrator_results_are_flat_and_have_status():
    """Ensure run_profile_for_repo returns a flat list of dicts with 'status'."""
    from pathlib import Path

    from firsttry.lazy_orchestrator import run_profile_for_repo
    from firsttry.run_profiles import dev_profile

    results, report = run_profile_for_repo(
        repo_root=Path.cwd(),
        profile=dev_profile(),
        report_path=None,
    )
    # must be a flat list of dicts with 'status'
    assert isinstance(results, list), f"Expected list, got {type(results)}"
    assert all(isinstance(r, dict) for r in results), f"Non-dict items: {results}"
    assert all("status" in r for r in results), f"Missing status: {results}"
    assert all("name" in r for r in results), f"Missing name: {results}"
    assert all("exit_code" in r for r in results), f"Missing exit_code: {results}"
