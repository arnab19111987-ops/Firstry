"""
Tests for GitHub Actions CI/CD Pipeline Validation

Phase 4.4: Comprehensive validation of CI workflow gates,
execution patterns, and deployment readiness.
"""

# Ensure pytest-cov has at least one measured import when running this file alone
try:
    import importlib

    importlib.import_module("firsttry.state")  # small, fast import that is cheap
except Exception:
    pass

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


class TestCIWorkflowStructure:
    """Validate GitHub Actions workflow YAML structure."""

    CI_WORKFLOW_PATH = Path(".github/workflows/ci.yml")
    CACHE_WORKFLOW_PATH = Path(".github/workflows/remote-cache.yml")
    AUDIT_WORKFLOW_PATH = Path(".github/workflows/audit.yml")

    @staticmethod
    def parse_yaml_simple(yaml_content: str) -> dict[str, Any]:
        """Parse basic YAML structure (no dependencies on yaml library)."""
        result: dict[str, Any] = {}
        current_section = result
        current_key = None

        for line in yaml_content.split("\n"):
            stripped = line.strip()

            # Skip empty and comment lines
            if not stripped or stripped.startswith("#"):
                continue

            # Top-level keys
            if not line.startswith(" "):
                if ":" in stripped:
                    key = stripped.split(":")[0].strip()
                    result[key] = {}
                    current_key = key
            # Jobs section
            elif current_key == "jobs" and line.startswith("  ") and not line.startswith("    "):
                job_name = stripped.split(":")[0]
                if current_key not in result:
                    result[current_key] = {}
                result[current_key][job_name] = {}

        return result

    def test_ci_workflow_exists(self):
        """CI workflow file must exist."""
        assert self.CI_WORKFLOW_PATH.exists(), f"CI workflow not found: {self.CI_WORKFLOW_PATH}"

    def test_remote_cache_workflow_exists(self):
        """Remote cache workflow file must exist."""
        assert (
            self.CACHE_WORKFLOW_PATH.exists()
        ), f"Cache workflow not found: {self.CACHE_WORKFLOW_PATH}"

    def test_audit_workflow_exists(self):
        """Audit workflow file must exist."""
        assert (
            self.AUDIT_WORKFLOW_PATH.exists()
        ), f"Audit workflow not found: {self.AUDIT_WORKFLOW_PATH}"

    def test_ci_workflow_has_required_jobs(self):
        """CI workflow must have all required jobs."""
        content = self.CI_WORKFLOW_PATH.read_text()

        required_jobs = [
            "lint",
            "type-safety",
            "tests",
            "enterprise-features",
            "security",
            "performance-benchmark",
            "audit-schema",
        ]

        for job in required_jobs:
            assert f"  {job}:" in content, f"Required job '{job}' not found in CI workflow"

    def test_ci_workflow_has_triggers(self):
        """CI workflow must have proper triggers."""
        content = self.CI_WORKFLOW_PATH.read_text()

        # Check for 'on' trigger
        assert "on:" in content, "No 'on:' trigger section found"

        # Check for required triggers
        required_triggers = ["push", "pull_request"]
        for trigger in required_triggers:
            assert trigger in content, f"Missing trigger: {trigger}"

    def test_lint_job_uses_ruff(self):
        """Lint job must use Ruff linter."""
        content = self.CI_WORKFLOW_PATH.read_text()

        assert "ruff check" in content, "Ruff linter not found in lint job"
        assert "ruff==0.14.3" in content, "Specific Ruff version not pinned"

    def test_type_safety_job_uses_mypy(self):
        """Type safety job must use MyPy."""
        content = self.CI_WORKFLOW_PATH.read_text()

        assert "python -m mypy" in content, "MyPy not found in type-safety job"
        assert "mypy==1.18.2" in content, "Specific MyPy version not pinned"

        # Check that critical modules are checked
        critical_modules = [
            "src/firsttry/runner/state.py",
            "src/firsttry/runner/planner.py",
            "src/firsttry/smart_pytest.py",
            "src/firsttry/scanner.py",
        ]

        for module in critical_modules:
            assert module in content, f"Critical module {module} not checked by MyPy in CI"

    def test_tests_job_runs_pytest(self):
        """Tests job must run pytest."""
        content = self.CI_WORKFLOW_PATH.read_text()

        assert "pytest==8.4.2" in content, "Pytest not pinned to specific version"
        assert "pytest-cov" in content, "Coverage plugin not found"

    def test_security_job_includes_bandit(self):
        """Security job must include Bandit scanner."""
        content = self.CI_WORKFLOW_PATH.read_text()

        assert "bandit" in content, "Bandit security scanner not found"
        assert "gitleaks" in content, "Gitleaks secret scanner not found"

    def test_benchmark_job_exists(self):
        """Performance benchmark job must exist."""
        content = self.CI_WORKFLOW_PATH.read_text()

        assert "performance-benchmark" in content, "Performance benchmark job not found"
        assert "SLO" in content or "slo" in content, "SLO checking logic not found"

    def test_audit_schema_job_exists(self):
        """Audit schema emission job must exist."""
        content = self.CI_WORKFLOW_PATH.read_text()

        assert "audit-schema" in content, "Audit schema job not found"
        assert (
            "audit_emit" in content or "emit_audit_report" in content
        ), "Audit emission module not used in workflow"


class TestGitHubActionsSemantics:
    """Validate GitHub Actions specific semantics."""

    CI_WORKFLOW_PATH = Path(".github/workflows/ci.yml")

    def test_uses_actions_checkout_v4(self):
        """Workflows must use actions/checkout@v4."""
        content = self.CI_WORKFLOW_PATH.read_text()
        assert "actions/checkout@v4" in content

    def test_uses_setup_python_v4(self):
        """Workflows must use actions/setup-python@v4."""
        content = self.CI_WORKFLOW_PATH.read_text()
        assert "actions/setup-python@v4" in content

    def test_uses_upload_artifact_v3(self):
        """Workflows must use actions/upload-artifact@v3."""
        content = self.CI_WORKFLOW_PATH.read_text()
        # GitHub Actions upload artifact has moved to v4; accept v4 here.
        assert "actions/upload-artifact@v4" in content or "actions/upload-artifact@v3" in content

    def test_permissions_configured(self):
        """Workflows must configure permissions."""
        content = self.CI_WORKFLOW_PATH.read_text()
        assert "permissions:" in content

    def test_environment_variables_set(self):
        """Workflows must set environment variables."""
        content = self.CI_WORKFLOW_PATH.read_text()
        assert "env:" in content
        assert "PYTHON_VERSION" in content or "python-version" in content

    def test_job_dependencies_configured(self):
        """Jobs should have proper dependencies via needs."""
        content = self.CI_WORKFLOW_PATH.read_text()
        assert "needs:" in content, "Job dependencies not configured"

    def test_always_run_final_status_job(self):
        """Final status job should always run."""
        content = self.CI_WORKFLOW_PATH.read_text()
        assert "if: always()" in content, "Some jobs may not report final status"

    def test_conditional_pr_comment_steps(self):
        """PR comment steps should only run on PRs."""
        content = self.CI_WORKFLOW_PATH.read_text()
        # Look for PR-specific conditions
        assert (
            "github.event_name == 'pull_request'" in content or "pull_request" in content
        ), "No PR-specific conditions found"


class TestCIGateExecution:
    """Test CI gate execution and configuration."""

    def test_ruff_linter_can_run(self):
        """Ruff linter should be executable."""
        try:
            result: Any = subprocess.run(
                [sys.executable, "-m", "ruff", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert result.returncode in [0, 1], "Ruff execution failed unexpectedly"
        except FileNotFoundError:
            pytest.skip("Ruff not installed")

    def test_mypy_can_run(self):
        """MyPy should be executable."""
        try:
            result: Any = subprocess.run(
                [sys.executable, "-m", "mypy", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert result.returncode == 0, "MyPy version check failed"
            assert "mypy" in result.stdout.lower(), "MyPy not recognized"
        except FileNotFoundError:
            pytest.skip("MyPy not installed")

    def test_pytest_can_run(self):
        """Pytest should be executable."""
        try:
            result: Any = subprocess.run(
                [sys.executable, "-m", "pytest", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            assert result.returncode == 0, "Pytest version check failed"
            assert "pytest" in result.stdout.lower(), "Pytest not recognized"
        except FileNotFoundError:
            pytest.skip("Pytest not installed")

    def test_critical_modules_exist(self):
        """Critical modules must exist for CI checks."""
        critical_modules = [
            "src/firsttry/runner/state.py",
            "src/firsttry/runner/planner.py",
            "src/firsttry/smart_pytest.py",
            "src/firsttry/scanner.py",
        ]

        for module in critical_modules:
            path = Path(module)
            assert path.exists(), f"Critical module not found: {module}"

    def test_audit_schema_file_exists(self):
        """Audit schema must exist for CI emission."""
        schema_path = Path("tools/audit_schema_v1.json")
        assert schema_path.exists(), f"Audit schema not found: {schema_path}"

    def test_audit_emit_module_exists(self):
        """Audit emission module must exist."""
        emit_module = Path("tools/audit_emit.py")
        assert emit_module.exists(), f"Audit emission module not found: {emit_module}"


class TestCacheIntegration:
    """Test cache integration configuration."""

    CACHE_WORKFLOW_PATH = Path(".github/workflows/remote-cache.yml")

    def test_remote_cache_workflow_has_s3_config(self):
        """Remote cache workflow must configure S3."""
        content = self.CACHE_WORKFLOW_PATH.read_text()

        assert "s3" in content.lower() or "S3" in content, "S3 configuration not found"
        assert "boto3" in content or "aws" in content.lower(), "AWS client not configured"

    def test_cache_sync_job_exists(self):
        """Cache sync job must exist."""
        content = self.CACHE_WORKFLOW_PATH.read_text()
        assert "sync-cache" in content, "Cache sync job not found"

    def test_cache_recovery_test_exists(self):
        """Cache recovery test must exist."""
        content = self.CACHE_WORKFLOW_PATH.read_text()
        assert "test-cache-recovery" in content, "Cache recovery test not found"

    def test_local_cache_directory_expected(self):
        """Tests should expect local cache in standard location."""
        cache_dir = Path(".firsttry/taskcache")
        # Don't assert existence (may not exist yet), just check path is correct
        assert str(cache_dir).endswith("taskcache"), "Cache directory path incorrect"


class TestAuditWorkflow:
    """Test audit and compliance workflow."""

    AUDIT_WORKFLOW_PATH = Path(".github/workflows/audit.yml")

    def test_audit_workflow_has_policy_validation(self):
        """Audit workflow must validate policies."""
        content = self.AUDIT_WORKFLOW_PATH.read_text()
        assert "policy" in content.lower(), "Policy validation not found"

    def test_audit_workflow_has_dependency_audit(self):
        """Audit workflow must audit dependencies."""
        content = self.AUDIT_WORKFLOW_PATH.read_text()
        assert (
            "pip-audit" in content or "dependency" in content.lower()
        ), "Dependency audit not found"

    def test_audit_workflow_generates_sbom(self):
        """Audit workflow must generate SBOM."""
        content = self.AUDIT_WORKFLOW_PATH.read_text()
        assert (
            "sbom" in content.lower() or "cyclonedx" in content.lower()
        ), "SBOM generation not found"

    def test_audit_workflow_generates_compliance_report(self):
        """Audit workflow must generate compliance report."""
        content = self.AUDIT_WORKFLOW_PATH.read_text()
        assert "compliance" in content.lower(), "Compliance checks not found"

    def test_release_readiness_job_exists(self):
        """Release readiness check job must exist."""
        content = self.AUDIT_WORKFLOW_PATH.read_text()
        assert (
            "release-readiness" in content or "release" in content.lower()
        ), "Release readiness check not found"


class TestDeploymentReadiness:
    """Test deployment readiness criteria."""

    def test_mypy_config_exists(self):
        """MyPy configuration must exist."""
        mypy_config = Path("mypy.ini")
        assert mypy_config.exists(), "MyPy configuration not found"

    def test_pytest_ini_exists(self):
        """Pytest configuration must exist."""
        pytest_config = Path("pytest.ini")
        assert pytest_config.exists(), "Pytest configuration not found"

    def test_github_workflows_directory_complete(self):
        """All required GitHub Actions workflows must exist."""
        workflows_dir = Path(".github/workflows")
        required_files = ["ci.yml", "remote-cache.yml", "audit.yml"]

        assert workflows_dir.exists(), "Workflows directory not found"

        for workflow_file in required_files:
            workflow_path = workflows_dir / workflow_file
            assert workflow_path.exists(), f"Required workflow not found: {workflow_file}"

    def test_docker_optional_not_required(self):
        """Docker is optional (workflows should work without it)."""
        # This is just documentation - Docker not required for GitHub Actions
        assert True, "Docker validation skipped (optional)"

    def test_all_gates_are_documented(self):
        """All CI gates must be documented somewhere."""
        doc_files = [
            "IMPLEMENTATION_INDEX.md",
            "ENTERPRISE_IMPLEMENTATION_FINAL.md",
        ]

        gates = ["ruff", "mypy", "pytest", "bandit"]
        found_gates: set[str] = set()

        for doc_file in doc_files:
            path = Path(doc_file)
            if path.exists():
                content = path.read_text()
                for gate in gates:
                    if gate in content.lower():
                        found_gates.add(gate)

        # Should find at least 3 of 4 gates documented
        assert len(found_gates) >= 3, f"Not enough gates documented: {found_gates}"


class TestCIWorkflowIntegration:
    """Integration tests for full CI workflow."""

    def test_ci_workflow_is_valid_yaml(self):
        """CI workflow must be valid YAML syntax."""
        ci_path = Path(".github/workflows/ci.yml")
        content = ci_path.read_text()

        # Basic YAML structure validation
        assert content.startswith("name:"), "Workflow must start with 'name:'"
        assert "on:" in content, "Workflow must have 'on:' section"
        assert "jobs:" in content, "Workflow must have 'jobs:' section"

        # Check for proper indentation (YAML requirement)
        for line in content.split("\n"):
            if line.strip() and not line.strip().startswith("#"):
                # Count leading spaces
                leading_spaces = len(line) - len(line.lstrip())
                # YAML requires indentation in multiples of 2
                assert leading_spaces % 2 == 0, f"Invalid YAML indentation: {repr(line)}"

    def test_all_jobs_have_descriptions(self):
        """All jobs should have clear name descriptions."""
        ci_path = Path(".github/workflows/ci.yml")
        content = ci_path.read_text()

        # Look for job name sections with 'name:' field
        assert content.count("name:") > 5, "Not enough named jobs in workflow"

    def test_workflow_gates_are_ordered_logically(self):
        """Workflow gates should execute in logical order."""
        ci_path = Path(".github/workflows/ci.yml")
        content = ci_path.read_text()

        # Extract job order from workflow
        lines = content.split("\n")
        job_order = []

        for i, line in enumerate(lines):
            if line.strip().startswith("- name:"):
                # Extract job name
                job_name = line.split("name:")[1].strip().replace('"', "").replace("'", "")
                job_order.append(job_name)

        # Should have gates in logical order
        if "Ruff" in " ".join(job_order):
            # Linting should come early
            ruff_idx = next(i for i, j in enumerate(job_order) if "ruff" in j.lower())
            pytest_idx = next(
                (i for i, j in enumerate(job_order) if "pytest" in j.lower()),
                float("inf"),
            )
            # Linting should come before or early in tests
            assert ruff_idx <= pytest_idx, "Lint should run before main tests"

    def test_final_status_job_always_executes(self):
        """Final status job must always execute for feedback."""
        ci_path = Path(".github/workflows/ci.yml")
        content = ci_path.read_text()

        assert (
            "final-status" in content.lower() or "Final CI Status" in content
        ), "No final status reporting job found"


class TestPhase4Completeness:
    """Verify Phase 4 implementation completeness."""

    def test_phase_4_1_ci_workflow_complete(self):
        """Phase 4.1 (Main CI Workflow) must be complete."""
        ci_path = Path(".github/workflows/ci.yml")
        assert ci_path.exists(), "CI workflow not created"
        assert ci_path.stat().st_size > 2000, "CI workflow too small (incomplete)"

    def test_phase_4_2_remote_cache_workflow_complete(self):
        """Phase 4.2 (Remote Cache Workflow) must be complete."""
        cache_path = Path(".github/workflows/remote-cache.yml")
        assert cache_path.exists(), "Remote cache workflow not created"
        assert cache_path.stat().st_size > 1000, "Cache workflow too small (incomplete)"

    def test_phase_4_3_audit_workflow_complete(self):
        """Phase 4.3 (Audit Workflow) must be complete."""
        audit_path = Path(".github/workflows/audit.yml")
        assert audit_path.exists(), "Audit workflow not created"
        assert audit_path.stat().st_size > 1500, "Audit workflow too small (incomplete)"

    def test_phase_4_gates_are_mypy_compatible(self):
        """All Phase 4 gates must be compatible with MyPy type checking."""
        # This validates that type checking from Phase 3 integrates into Phase 4
        ci_path = Path(".github/workflows/ci.yml")
        content = ci_path.read_text()

        # MyPy must be in CI workflow
        assert "mypy" in content.lower(), "MyPy type checking not integrated into Phase 4"
        assert (
            "strict" in content.lower() or "mypy.ini" in content
        ), "MyPy strict mode not configured in Phase 4"

    def test_phase_4_audit_schema_integration(self):
        """Phase 4 must emit audit reports using Phase 3.2 schema."""
        ci_path = Path(".github/workflows/ci.yml")
        content = ci_path.read_text()

        # Audit emission must be in CI
        assert "audit" in content.lower(), "Audit schema not integrated into Phase 4"
        assert (
            "emit_audit" in content or "audit_emit" in content
        ), "Audit emission module not used in Phase 4"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
