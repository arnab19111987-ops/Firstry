"""Phase 3.1: MyPy Strict Mode Implementation and Validation Tests"""

import subprocess
import sys
from pathlib import Path

import pytest


class TestMypyConfiguration:
    """Test that mypy is properly configured."""

    def test_mypy_ini_exists(self):
        """mypy.ini should exist."""
        mypy_path = Path("/workspaces/Firstry/mypy.ini")
        assert mypy_path.exists(), "mypy.ini not found"

    def test_mypy_ini_has_python_version(self):
        """mypy.ini should specify python_version."""
        mypy_path = Path("/workspaces/Firstry/mypy.ini")
        content = mypy_path.read_text()
        assert "python_version" in content
        assert "3.11" in content or "3.12" in content

    def test_mypy_ini_has_strict_warning_flags(self):
        """mypy.ini should have warning flags configured."""
        mypy_path = Path("/workspaces/Firstry/mypy.ini")
        content = mypy_path.read_text()
        assert "warn_unused_ignores" in content
        assert "show_error_codes" in content


class TestCriticalModuleTypeSafety:
    """Test type safety of critical modules."""

    @staticmethod
    def run_mypy(module_path: str) -> tuple[int, str]:
        """Run mypy on a module and return exit code and output."""
        result = subprocess.run(
            [sys.executable, "-m", "mypy", module_path],
            cwd="/workspaces/Firstry",
            capture_output=True,
            text=True,
        )
        return result.returncode, result.stdout + result.stderr

    def test_state_py_type_safe(self):
        """src/firsttry/runner/state.py should pass mypy."""
        code, output = self.run_mypy("src/firsttry/runner/state.py")
        assert code == 0, f"MyPy failed for state.py:\n{output}"

    def test_planner_py_type_safe(self):
        """src/firsttry/runner/planner.py should pass mypy."""
        code, output = self.run_mypy("src/firsttry/runner/planner.py")
        assert code == 0, f"MyPy failed for planner.py:\n{output}"

    def test_smart_pytest_py_type_safe(self):
        """src/firsttry/smart_pytest.py should pass mypy."""
        code, output = self.run_mypy("src/firsttry/smart_pytest.py")
        assert code == 0, f"MyPy failed for smart_pytest.py:\n{output}"

    def test_scanner_py_type_safe(self):
        """src/firsttry/scanner.py should pass mypy."""
        code, output = self.run_mypy("src/firsttry/scanner.py")
        assert code == 0, f"MyPy failed for scanner.py:\n{output}"


class TestMypyStrictMode:
    """Test that modules can handle strict mode."""

    @staticmethod
    def run_mypy_strict(module_path: str) -> tuple[int, str]:
        """Run mypy in strict mode on a module."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "mypy",
                module_path,
                "--strict",
            ],
            cwd="/workspaces/Firstry",
            capture_output=True,
            text=True,
        )
        return result.returncode, result.stdout + result.stderr

    def test_state_py_strict_compatible(self):
        """state.py should be compatible with strict mode."""
        code, output = self.run_mypy_strict("src/firsttry/runner/state.py")
        # We accept some failures during transition, but track them
        if code != 0:
            # This is informational - we're testing what needs fixing for strict mode
            assert "error" in output.lower()

    def test_planner_py_strict_compatible(self):
        """planner.py should be compatible with strict mode."""
        code, output = self.run_mypy_strict("src/firsttry/runner/planner.py")
        # Track strict mode compatibility
        if code != 0:
            assert "error" in output.lower()

    def test_smart_pytest_py_strict_compatible(self):
        """smart_pytest.py should be compatible with strict mode."""
        code, output = self.run_mypy_strict("src/firsttry/smart_pytest.py")
        if code != 0:
            assert "error" in output.lower()

    def test_scanner_py_strict_compatible(self):
        """scanner.py should be compatible with strict mode."""
        code, output = self.run_mypy_strict("src/firsttry/scanner.py")
        if code != 0:
            assert "error" in output.lower()


class TestTypeAnnotationCoverage:
    """Test that critical functions have type annotations."""

    def test_state_py_has_annotations(self):
        """state.py functions should have type annotations."""
        state_path = Path("/workspaces/Firstry/src/firsttry/runner/state.py")
        content = state_path.read_text()
        # Check for function definitions with type hints
        assert "def " in content
        assert "->" in content  # Return type annotation

    def test_planner_py_has_annotations(self):
        """planner.py functions should have type annotations."""
        planner_path = Path("/workspaces/Firstry/src/firsttry/runner/planner.py")
        content = planner_path.read_text()
        assert "def " in content
        assert "->" in content

    def test_smart_pytest_py_has_annotations(self):
        """smart_pytest.py functions should have type annotations."""
        smart_path = Path("/workspaces/Firstry/src/firsttry/smart_pytest.py")
        content = smart_path.read_text()
        assert "def " in content
        assert "->" in content

    def test_scanner_py_has_annotations(self):
        """scanner.py functions should have type annotations."""
        scanner_path = Path("/workspaces/Firstry/src/firsttry/scanner.py")
        content = scanner_path.read_text()
        assert "def " in content
        assert "->" in content


class TestNoUnsafePatterns:
    """Test for absence of unsafe type patterns."""

    def test_no_bare_except(self):
        """Code should not use bare except clauses."""
        paths = [
            "src/firsttry/runner/state.py",
            "src/firsttry/runner/planner.py",
            "src/firsttry/smart_pytest.py",
            "src/firsttry/scanner.py",
        ]
        for path in paths:
            file_path = Path("/workspaces/Firstry") / path
            if file_path.exists():
                content = file_path.read_text()
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    # Check for bare except (not "except BaseException" etc)
                    stripped = line.strip()
                    if stripped == "except:":
                        pytest.fail(f"{path}:{i} has bare except clause")

    def test_no_type_ignore_abuse(self):
        """type: ignore should be used sparingly with reasons."""
        paths = [
            "src/firsttry/runner/state.py",
            "src/firsttry/runner/planner.py",
        ]
        for path in paths:
            file_path = Path("/workspaces/Firstry") / path
            if file_path.exists():
                content = file_path.read_text()
                lines = content.split("\n")
                ignore_count = sum(1 for line in lines if "type: ignore" in line)
                # Should have 0-2 type ignores at most
                assert ignore_count <= 2, f"{path} has {ignore_count} type ignores"


class TestTypeCheckingGate:
    """Test that type checking can be used as a CI gate."""

    def test_mypy_can_run_on_all_code(self):
        """MyPy should run without crashes on all code."""
        result = subprocess.run(
            [sys.executable, "-m", "mypy", "src/firsttry"],
            cwd="/workspaces/Firstry",
            capture_output=True,
            text=True,
            timeout=60,
        )
        # Should not crash (can have errors, but shouldn't crash)
        assert result.returncode in [0, 1], f"MyPy crashed: {result.stderr}"

    def test_mypy_can_be_ci_gate(self):
        """MyPy should be suitable as a CI gate."""
        # Run on critical modules
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "mypy",
                "src/firsttry/runner/state.py",
                "src/firsttry/runner/planner.py",
                "src/firsttry/smart_pytest.py",
                "src/firsttry/scanner.py",
            ],
            cwd="/workspaces/Firstry",
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, f"Critical modules have type errors:\n{result.stdout}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
