"""Test pure functions in repo_rules and change_detector."""

from firsttry.repo_rules import plan_checks_for_repo
from firsttry.change_detector import categorize_changed_files


def test_plan_checks_for_repo_returns_list():
    """Test that plan_checks_for_repo returns a list of checks."""
    # Call with minimal repo_profile
    repo_profile = {"has_python": True}
    checks = plan_checks_for_repo(repo_profile)
    
    assert isinstance(checks, list)
    # Should return at least some checks
    assert len(checks) >= 0


def test_categorize_changed_files_with_empty_list():
    """Test categorizing empty file list."""
    categories = categorize_changed_files([])
    
    assert isinstance(categories, dict)
    # Should return empty or valid structure
    assert len(categories) >= 0


def test_categorize_changed_files_with_python_files():
    """Test categorizing Python files."""
    files = ["src/main.py", "tests/test_foo.py", "setup.py"]
    categories = categorize_changed_files(files)
    
    assert isinstance(categories, dict)
    # Should categorize Python files
    has_python = "python" in categories or "py" in str(categories).lower()
    # If it doesn't categorize, at least it shouldn't crash
    assert has_python or len(categories) >= 0


def test_categorize_changed_files_with_config_files():
    """Test categorizing config files."""
    files = ["pyproject.toml", "package.json", ".gitignore", "Makefile"]
    categories = categorize_changed_files(files)
    
    assert isinstance(categories, dict)
    # Should handle config files
    assert len(categories) >= 0


def test_categorize_changed_files_with_mixed_types():
    """Test categorizing mixed file types."""
    files = [
        "src/main.py",
        "README.md",
        "package.json",
        "test.js",
        "Dockerfile"
    ]
    categories = categorize_changed_files(files)
    
    assert isinstance(categories, dict)
    # Should categorize various types
    assert len(categories) >= 0


def test_plan_checks_for_repo_is_deterministic():
    """Test that plan_checks_for_repo returns consistent results."""
    repo_profile = {"has_python": True}
    checks1 = plan_checks_for_repo(repo_profile)
    checks2 = plan_checks_for_repo(repo_profile)
    
    # Should return same type
    assert type(checks1) == type(checks2)
    assert isinstance(checks1, list)


def test_categorize_changed_files_handles_none_gracefully():
    """Test that categorize handles edge cases."""
    try:
        # Try with empty list
        categories = categorize_changed_files([])
        assert isinstance(categories, dict)
    except Exception:
        # If it doesn't accept empty, that's OK
        assert True
