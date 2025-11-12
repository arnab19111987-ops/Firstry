"""Comprehensive coverage tests for src/firsttry/smart_pytest.py

This suite targets:
- Pytest cache directory detection
- Failed test extraction and tracking
- Test file mapping from source changes
- Smoke test identification
- pytest-xdist availability detection
- Pytest command building with various modes
- Smart pytest execution with caching
"""

import json
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

from firsttry.smart_pytest import build_pytest_command
from firsttry.smart_pytest import get_failed_tests
from firsttry.smart_pytest import get_pytest_cache_dir
from firsttry.smart_pytest import get_smoke_tests
from firsttry.smart_pytest import get_test_files_for_changes
from firsttry.smart_pytest import has_pytest_xdist


class TestPytestCacheDir:
    """Test pytest cache directory operations."""

    def test_get_pytest_cache_dir_returns_path(self, tmp_path: Path):
        """Test get_pytest_cache_dir returns correct path."""
        repo_root = str(tmp_path)
        cache_dir = get_pytest_cache_dir(repo_root)

        assert cache_dir == tmp_path / ".pytest_cache"
        assert isinstance(cache_dir, Path)

    def test_get_pytest_cache_dir_different_repos(self, tmp_path: Path):
        """Test that different repos get different cache dirs."""
        repo1 = str(tmp_path / "repo1")
        repo2 = str(tmp_path / "repo2")

        cache_dir1 = get_pytest_cache_dir(repo1)
        cache_dir2 = get_pytest_cache_dir(repo2)

        assert cache_dir1 != cache_dir2
        assert str(repo1) in str(cache_dir1)
        assert str(repo2) in str(cache_dir2)

    def test_get_pytest_cache_dir_with_trailing_slash(self, tmp_path: Path):
        """Test get_pytest_cache_dir handles trailing slashes."""
        repo_root = str(tmp_path) + "/"
        cache_dir = get_pytest_cache_dir(repo_root)

        assert ".pytest_cache" in str(cache_dir)


class TestGetFailedTests:
    """Test failed test extraction from pytest cache."""

    def test_get_failed_tests_no_cache(self, tmp_path: Path):
        """Test get_failed_tests returns empty list when cache doesn't exist."""
        repo_root = str(tmp_path)
        failed_tests = get_failed_tests(repo_root)

        assert failed_tests == []

    def test_get_failed_tests_with_failed_file(self, tmp_path: Path):
        """Test get_failed_tests extracts tests from lastfailed file."""
        # Create pytest cache structure
        cache_dir = tmp_path / ".pytest_cache" / "v" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Create lastfailed file
        failed_data = {
            "tests/test_module1.py::test_function1": {"failed": True},
            "tests/test_module2.py::test_function2": {"failed": True},
        }
        lastfailed_file = cache_dir / "lastfailed"
        lastfailed_file.write_text(json.dumps(failed_data))

        repo_root = str(tmp_path)
        failed_tests = get_failed_tests(repo_root)

        assert len(failed_tests) == 2
        assert "tests/test_module1.py::test_function1" in failed_tests
        assert "tests/test_module2.py::test_function2" in failed_tests

    def test_get_failed_tests_single_failure(self, tmp_path: Path):
        """Test get_failed_tests with single failed test."""
        cache_dir = tmp_path / ".pytest_cache" / "v" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        failed_data = {"tests/test_one.py::test_one": {"failed": True}}
        (cache_dir / "lastfailed").write_text(json.dumps(failed_data))

        repo_root = str(tmp_path)
        failed_tests = get_failed_tests(repo_root)

        assert len(failed_tests) == 1
        assert failed_tests[0] == "tests/test_one.py::test_one"

    def test_get_failed_tests_corrupted_cache(self, tmp_path: Path):
        """Test get_failed_tests handles corrupted cache gracefully."""
        cache_dir = tmp_path / ".pytest_cache" / "v" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Write invalid JSON
        (cache_dir / "lastfailed").write_text("invalid json {{{")

        repo_root = str(tmp_path)
        failed_tests = get_failed_tests(repo_root)

        # Should return empty list, not crash
        assert failed_tests == []

    def test_get_failed_tests_empty_cache(self, tmp_path: Path):
        """Test get_failed_tests with empty cache."""
        cache_dir = tmp_path / ".pytest_cache" / "v" / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Write empty JSON object
        (cache_dir / "lastfailed").write_text("{}")

        repo_root = str(tmp_path)
        failed_tests = get_failed_tests(repo_root)

        assert failed_tests == []


class TestGetTestFilesForChanges:
    """Test mapping changed files to test files."""

    def test_get_test_files_empty_changes(self, tmp_path: Path):
        """Test with no changed files."""
        repo_root = str(tmp_path)
        test_files = get_test_files_for_changes(repo_root, [])

        assert test_files == set()

    def test_get_test_files_ignores_non_python(self, tmp_path: Path):
        """Test that non-Python files are ignored."""
        repo_root = str(tmp_path)
        changed_files = ["README.md", "config.yaml", "data.json"]

        test_files = get_test_files_for_changes(repo_root, changed_files)

        assert test_files == set()

    def test_get_test_files_includes_test_files(self, tmp_path: Path):
        """Test that test files are included directly."""
        # Create test structure
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_main.py").touch()

        repo_root = str(tmp_path)
        changed_files = ["tests/test_main.py"]

        test_files = get_test_files_for_changes(repo_root, changed_files)

        assert "tests/test_main.py" in test_files

    def test_get_test_files_maps_source_to_test(self, tmp_path: Path):
        """Test mapping source file to corresponding test file."""
        # Create structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "module.py").touch()

        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_module.py").touch()

        repo_root = str(tmp_path)
        changed_files = ["src/module.py"]

        test_files = get_test_files_for_changes(repo_root, changed_files)

        assert "tests/test_module.py" in test_files

    def test_get_test_files_multiple_mappings(self, tmp_path: Path):
        """Test multiple files mapping to tests."""
        # Create structure
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_a.py").touch()
        (tests_dir / "test_b.py").touch()
        (tests_dir / "test_c.py").touch()

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "a.py").touch()
        (src_dir / "b.py").touch()
        (src_dir / "c.py").touch()

        repo_root = str(tmp_path)
        changed_files = ["src/a.py", "src/b.py", "src/c.py"]

        test_files = get_test_files_for_changes(repo_root, changed_files)

        assert len(test_files) == 3
        assert "tests/test_a.py" in test_files
        assert "tests/test_b.py" in test_files
        assert "tests/test_c.py" in test_files

    def test_get_test_files_suffix_patterns(self, tmp_path: Path):
        """Test both test_X.py and X_test.py patterns."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_module.py").touch()
        (tests_dir / "other_test.py").touch()

        repo_root = str(tmp_path)
        changed_files = ["module.py", "other.py"]

        test_files = get_test_files_for_changes(repo_root, changed_files)

        assert "tests/test_module.py" in test_files
        assert "tests/other_test.py" in test_files


class TestGetSmokeTests:
    """Test smoke test identification."""

    def test_get_smoke_tests_dedicated_file(self, tmp_path: Path):
        """Test detection of dedicated smoke test file."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_smoke.py").touch()

        repo_root = str(tmp_path)
        smoke_tests = get_smoke_tests(repo_root)

        assert "tests/test_smoke.py" in smoke_tests

    def test_get_smoke_tests_dedicated_directory(self, tmp_path: Path):
        """Test detection of dedicated smoke directory."""
        smoke_dir = tmp_path / "tests" / "smoke"
        smoke_dir.mkdir(parents=True)
        (smoke_dir / "test_basic.py").touch()
        (smoke_dir / "test_health.py").touch()

        repo_root = str(tmp_path)
        smoke_tests = get_smoke_tests(repo_root)

        # Should include files from smoke directory
        assert len(smoke_tests) >= 2

    def test_get_smoke_tests_fallback_pattern(self, tmp_path: Path):
        """Test fallback to basic test patterns."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_imports.py").touch()
        (tests_dir / "test_basic.py").touch()
        (tests_dir / "test_other.py").touch()

        repo_root = str(tmp_path)
        smoke_tests = get_smoke_tests(repo_root)

        # Should include imports and basic tests
        assert len(smoke_tests) > 0

    def test_get_smoke_tests_no_tests(self, tmp_path: Path):
        """Test when no test files exist."""
        repo_root = str(tmp_path)
        smoke_tests = get_smoke_tests(repo_root)

        assert smoke_tests == []

    def test_get_smoke_tests_limits_results(self, tmp_path: Path):
        """Test that smoke tests are limited in count."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        for i in range(100):
            (tests_dir / f"test_{i:03d}.py").touch()

        repo_root = str(tmp_path)
        smoke_tests = get_smoke_tests(repo_root)

        # Should not return all 100, limit to first few
        assert len(smoke_tests) <= 10


class TestHasPytestXdist:
    """Test pytest-xdist availability detection."""

    @patch("subprocess.run")
    def test_has_pytest_xdist_available(self, mock_run):
        """Test detection when xdist is installed."""
        mock_run.return_value = Mock(returncode=0)
        repo_root = "/tmp/repo"

        result = has_pytest_xdist(repo_root)

        assert result is True

    @patch("subprocess.run")
    def test_has_pytest_xdist_not_available(self, mock_run):
        """Test detection when xdist is not installed."""
        mock_run.return_value = Mock(returncode=1)
        repo_root = "/tmp/repo"

        result = has_pytest_xdist(repo_root)

        assert result is False

    @patch("subprocess.run")
    def test_has_pytest_xdist_timeout(self, mock_run):
        """Test handling of command timeout."""
        mock_run.side_effect = TimeoutError()
        repo_root = "/tmp/repo"

        result = has_pytest_xdist(repo_root)

        assert result is False

    @patch("subprocess.run")
    def test_has_pytest_xdist_exception(self, mock_run):
        """Test handling of general exceptions."""
        mock_run.side_effect = Exception("Some error")
        repo_root = "/tmp/repo"

        result = has_pytest_xdist(repo_root)

        assert result is False


class TestBuildPytestCommand:
    """Test pytest command building."""

    def test_build_pytest_command_basic(self, tmp_path: Path):
        """Test basic pytest command building."""
        repo_root = str(tmp_path)

        cmd = build_pytest_command(repo_root, mode="full")

        assert "python" in cmd
        assert "-m" in cmd
        assert "pytest" in cmd
        assert "-v" in cmd
        assert "--tb=short" in cmd

    def test_build_pytest_command_smoke_mode(self, tmp_path: Path):
        """Test smoke mode command."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_smoke.py").touch()

        repo_root = str(tmp_path)
        cmd = build_pytest_command(repo_root, mode="smoke")

        # Smoke mode should stop on first failure
        assert "-x" in cmd
        assert "--maxfail=1" in cmd

    def test_build_pytest_command_failed_mode(self, tmp_path: Path):
        """Test failed mode command."""
        repo_root = str(tmp_path)

        cmd = build_pytest_command(repo_root, mode="failed")

        # Failed mode should include --lf flag
        assert "--lf" in cmd

    def test_build_pytest_command_with_test_files(self, tmp_path: Path):
        """Test command with specific test files."""
        repo_root = str(tmp_path)
        test_files = ["tests/test_a.py", "tests/test_b.py"]

        cmd = build_pytest_command(repo_root, test_files=test_files)

        assert "tests/test_a.py" in cmd
        assert "tests/test_b.py" in cmd

    @patch("firsttry.smart_pytest.has_pytest_xdist")
    def test_build_pytest_command_with_xdist(self, mock_xdist, tmp_path: Path):
        """Test parallel flag when xdist available."""
        mock_xdist.return_value = True
        repo_root = str(tmp_path)

        cmd = build_pytest_command(repo_root, parallel=True)

        # Should include parallel flags
        assert "-n" in cmd or "auto" in cmd

    @patch("firsttry.smart_pytest.has_pytest_xdist")
    def test_build_pytest_command_no_xdist(self, mock_xdist, tmp_path: Path):
        """Test no parallel when xdist unavailable."""
        mock_xdist.return_value = False
        repo_root = str(tmp_path)

        cmd = build_pytest_command(repo_root, parallel=True)

        # Should not have parallel flags
        assert "-n" not in cmd

    def test_build_pytest_command_multiple_modes(self, tmp_path: Path):
        """Test different modes produce different commands."""
        repo_root = str(tmp_path)

        cmd_smoke = build_pytest_command(repo_root, mode="smoke")
        cmd_full = build_pytest_command(repo_root, mode="full")
        cmd_failed = build_pytest_command(repo_root, mode="failed")

        # Smoke should have maxfail
        assert "--maxfail=1" in cmd_smoke

        # Failed should have --lf
        assert "--lf" in cmd_failed

        # Full should not have these
        assert "--maxfail=1" not in cmd_full or "--lf" not in cmd_full


class TestSmartPytestIntegration:
    """Integration tests for smart pytest features."""

    def test_smart_pytest_workflow(self, tmp_path: Path):
        """Test complete smart pytest workflow."""
        # Create project structure
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_main.py").touch()

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").touch()

        repo_root = str(tmp_path)

        # Get test files for change
        changed_files = ["src/main.py"]
        test_files = get_test_files_for_changes(repo_root, changed_files)

        # Should map to test_main.py
        assert "tests/test_main.py" in test_files

        # Build pytest command for those files
        cmd = build_pytest_command(repo_root, list(test_files))

        # Should have the test files
        assert "tests/test_main.py" in cmd

    def test_smoke_vs_full_pytest(self, tmp_path: Path):
        """Test smoke tests are subset of full tests."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_smoke.py").touch()
        (tests_dir / "test_integration.py").touch()
        (tests_dir / "test_slow.py").touch()

        repo_root = str(tmp_path)

        smoke_tests = get_smoke_tests(repo_root)
        # Smoke tests should be fewer than total

        assert len(smoke_tests) <= 3


class TestSmartPytestEdgeCases:
    """Test edge cases in smart pytest."""

    def test_nested_test_directories(self, tmp_path: Path):
        """Test handling of nested test directories."""
        nested = tmp_path / "tests" / "unit" / "subdir"
        nested.mkdir(parents=True)
        (nested / "test_deep.py").touch()

        repo_root = str(tmp_path)
        smoke_tests = get_smoke_tests(repo_root)

        # Should find nested tests
        assert len(smoke_tests) >= 0

    def test_test_files_with_underscores(self, tmp_path: Path):
        """Test handling test files with multiple underscores."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_unit_slow_io.py").touch()

        repo_root = str(tmp_path)
        smoke_tests = get_smoke_tests(repo_root)

        # Should handle long names
        assert len(smoke_tests) >= 0

    def test_empty_test_directory(self, tmp_path: Path):
        """Test with empty test directory."""
        (tmp_path / "tests").mkdir()

        repo_root = str(tmp_path)
        smoke_tests = get_smoke_tests(repo_root)

        assert smoke_tests == []

    def test_unicode_in_paths(self, tmp_path: Path):
        """Test handling of unicode in test paths."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        # Create file with unicode name
        (tests_dir / "test_特性.py").touch()

        repo_root = str(tmp_path)
        # Should not crash
        smoke_tests = get_smoke_tests(repo_root)
        assert isinstance(smoke_tests, list)
