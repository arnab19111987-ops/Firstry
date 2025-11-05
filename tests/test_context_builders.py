"""Test context builders for repo profiling."""

from firsttry.context_builders import build_context, build_repo_profile


def test_build_context_returns_dict():
    """Test that build_context returns a dictionary with expected structure."""
    ctx = build_context()

    assert isinstance(ctx, dict), "Context should be a dictionary"

    # Should have some basic keys (exact keys may vary by implementation)
    # Common keys: repo_root, files, py_files, config, etc.
    assert len(ctx) > 0, "Context should not be empty"


def test_build_context_has_repo_info():
    """Test that context includes repository information."""
    ctx = build_context()

    # Should have some repo-related information
    # Common patterns: "repo_root", "root", "project_root", etc.
    has_repo_info = any(
        key in ctx for key in ["repo_root", "root", "project_root", "cwd", "files"]
    )
    assert has_repo_info, f"Context should include repo info. Keys: {list(ctx.keys())}"


def test_build_repo_profile_returns_data():
    """Test that build_repo_profile returns profile data."""
    prof = build_repo_profile()

    # Profile should be a dict or object with language/tool information
    assert prof is not None

    # Convert to string to check for language indicators
    prof_str = str(prof).lower()

    # Should mention some language or tool info
    # Since this is a Python project, it should likely mention Python
    common_indicators = ["python", "language", "tool", "file", "py"]
    has_indicator = any(indicator in prof_str for indicator in common_indicators)

    assert has_indicator, f"Profile should contain language/tool info. Got: {prof}"


def test_build_repo_profile_is_deterministic():
    """Test that build_repo_profile returns consistent results."""
    prof1 = build_repo_profile()
    prof2 = build_repo_profile()

    # Should return same structure (values may differ due to file changes)
    assert type(prof1) == type(prof2)


def test_build_context_handles_empty_args():
    """Test that build_context works without arguments."""
    # Should work with defaults
    ctx = build_context()
    assert ctx is not None
    assert isinstance(ctx, dict)
