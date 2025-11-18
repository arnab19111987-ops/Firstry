"""Tests for audit schema and emission."""

import json
import tempfile
from pathlib import Path

import pytest

from tools.audit_emit import (
    emit_audit_json,
    emit_audit_report,
    emit_audit_summary,
    load_schema,
    validate_audit_report,
)


class TestAuditSchemaLoading:
    """Tests for loading and validating the audit schema."""

    def test_audit_schema_exists(self):
        """Audit schema file should exist."""
        schema_path = Path(__file__).parent.parent.parent / "tools" / "audit_schema_v1.json"
        assert schema_path.exists(), "audit_schema_v1.json not found"

    def test_load_schema_returns_dict(self):
        """load_schema() should return a valid schema dict."""
        schema = load_schema()
        assert isinstance(schema, dict)
        assert "$schema" in schema
        assert "title" in schema
        assert "type" in schema

    def test_schema_has_required_properties(self):
        """Schema should define required properties."""
        schema = load_schema()
        assert "properties" in schema
        required = schema.get("required", [])
        assert "version" in required
        assert "timestamp" in required
        assert "status" in required
        assert "scores" in required
        assert "gates" in required


class TestAuditReportGeneration:
    """Tests for generating valid audit reports."""

    @pytest.fixture
    def minimal_report_params(self):
        """Minimal parameters for audit report generation."""
        return {
            "overall_score": 85,
            "category_scores": {
                "architecture": 90,
                "security": 95,
                "performance": 88,
                "test_coverage": 75,
                "enforcement": 80,
                "ci_parity": 85,
            },
            "gates_executed": [
                {
                    "name": "ruff",
                    "status": "pass",
                    "duration_ms": 500,
                    "exit_code": 0,
                    "issues_found": 0,
                    "autofixable": 0,
                }
            ],
            "repository": {
                "owner": "test-org",
                "name": "test-repo",
                "url": "https://github.com/test-org/test-repo",
            },
            "branch": "main",
            "commit_info": {
                "sha": "abc123def456",
                "author": "Test User",
                "message": "Test commit",
            },
            "tier": "pro",
        }

    def test_emit_audit_report_returns_dict(self, minimal_report_params):
        """emit_audit_report should return a dict."""
        report = emit_audit_report(**minimal_report_params)
        assert isinstance(report, dict)

    def test_emit_audit_report_has_required_fields(self, minimal_report_params):
        """Generated report should have all required fields."""
        report = emit_audit_report(**minimal_report_params)
        required = [
            "version",
            "timestamp",
            "repository",
            "branch",
            "commit",
            "tier",
            "status",
            "scores",
            "gates",
            "cache_metrics",
            "security",
            "compliance",
            "metadata",
        ]
        for field in required:
            assert field in report, f"Missing field: {field}"

    def test_emit_audit_report_version_format(self, minimal_report_params):
        """Report version should follow semantic versioning."""
        report = emit_audit_report(**minimal_report_params)
        assert report["version"] == "1.0.0"

    def test_emit_audit_report_status_calculation_pass(self, minimal_report_params):
        """Status should be 'pass' when all gates pass."""
        report = emit_audit_report(**minimal_report_params)
        assert report["status"] == "pass"

    def test_emit_audit_report_status_calculation_fail(self, minimal_report_params):
        """Status should be 'fail' when any gate fails."""
        minimal_report_params["gates_executed"] = [
            {
                "name": "ruff",
                "status": "fail",
                "duration_ms": 500,
                "exit_code": 1,
                "issues_found": 5,
            }
        ]
        report = emit_audit_report(**minimal_report_params)
        assert report["status"] == "fail"

    def test_emit_audit_report_status_calculation_partial(self, minimal_report_params):
        """Status should be 'partial' when gates are skipped."""
        minimal_report_params["gates_executed"] = [
            {
                "name": "ruff",
                "status": "pass",
                "duration_ms": 500,
                "exit_code": 0,
            },
            {
                "name": "mypy",
                "status": "skip",
                "duration_ms": 0,
            },
        ]
        report = emit_audit_report(**minimal_report_params)
        assert report["status"] == "partial"

    def test_emit_audit_report_gate_summary(self, minimal_report_params):
        """Gate summary should accurately count results."""
        minimal_report_params["gates_executed"] = [
            {"name": "ruff", "status": "pass", "duration_ms": 100},
            {"name": "mypy", "status": "pass", "duration_ms": 200},
            {"name": "pytest", "status": "fail", "duration_ms": 300},
            {"name": "bandit", "status": "skip", "duration_ms": 0},
        ]
        report = emit_audit_report(**minimal_report_params)
        summary = report["gates"]["summary"]
        assert summary["total"] == 4
        assert summary["passed"] == 2
        assert summary["failed"] == 1
        assert summary["skipped"] == 1

    def test_emit_audit_report_scores_preserved(self, minimal_report_params):
        """Scores should be preserved in output."""
        report = emit_audit_report(**minimal_report_params)
        assert report["scores"]["overall"] == 85
        assert report["scores"]["categories"]["architecture"] == 90
        assert report["scores"]["categories"]["security"] == 95

    def test_emit_audit_report_with_optional_fields(self, minimal_report_params):
        """Optional fields should be included when provided."""
        minimal_report_params["cache_metrics"] = {
            "total_hits": 10,
            "total_misses": 2,
            "hit_rate": 0.833,
        }
        minimal_report_params["security"] = {
            "secrets_found": 0,
            "vulnerabilities": {"critical": 0},
        }
        minimal_report_params["compliance"] = {
            "policy_enforced": True,
            "sbom_generated": True,
        }

        report = emit_audit_report(**minimal_report_params)
        assert report["cache_metrics"]["hit_rate"] == 0.833
        assert report["security"]["secrets_found"] == 0
        assert report["compliance"]["sbom_generated"] is True

    def test_emit_audit_report_metadata_captured(self, minimal_report_params):
        """Metadata should include environment info."""
        minimal_report_params["metadata"] = {
            "python_version": "3.11.7",
            "environment": "local",
            "audit_duration_ms": 6500,
        }
        report = emit_audit_report(**minimal_report_params)
        assert report["metadata"]["python_version"] == "3.11.7"
        assert report["metadata"]["environment"] == "local"


class TestAuditReportValidation:
    """Tests for validating audit reports against schema."""

    def test_validate_audit_report_passes_for_valid_report(self):
        """Valid reports should pass validation."""
        valid_report = {
            "version": "1.0.0",
            "timestamp": "2025-11-08T11:23:32Z",
            "repository": {
                "owner": "test",
                "name": "repo",
                "url": "https://github.com/test/repo",
            },
            "branch": "main",
            "commit": {"sha": "abc123def456", "author": "user", "message": "msg"},
            "tier": "pro",
            "status": "pass",
            "scores": {
                "overall": 85,
                "categories": {"architecture": 85},
            },
            "gates": {
                "executed": [],
                "summary": {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
            },
            "cache_metrics": {},
            "security": {},
            "compliance": {},
            "metadata": {},
        }
        is_valid, errors = validate_audit_report(valid_report)
        assert is_valid is True
        assert errors == []

    def test_validate_audit_report_fails_for_missing_required_field(self):
        """Reports missing required fields should fail validation."""
        invalid_report = {"version": "1.0.0"}  # Missing most required fields
        is_valid, errors = validate_audit_report(invalid_report)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_audit_report_fails_for_invalid_version_format(self):
        """Invalid version format should fail validation."""
        invalid_report = {
            "version": "invalid",  # Should be semantic versioning
            "timestamp": "2025-11-08T11:23:32Z",
            "repository": {
                "owner": "test",
                "name": "repo",
                "url": "https://github.com/test/repo",
            },
            "branch": "main",
            "commit": {"sha": "abc123def456", "author": "user", "message": "msg"},
            "tier": "pro",
            "status": "pass",
            "scores": {"overall": 85, "categories": {}},
            "gates": {"executed": [], "summary": {}},
            "cache_metrics": {},
            "security": {},
            "compliance": {},
        }
        is_valid, errors = validate_audit_report(invalid_report)
        assert is_valid is False

    def test_validate_audit_report_fails_for_invalid_status(self):
        """Invalid status should fail validation."""
        invalid_report = {
            "version": "1.0.0",
            "timestamp": "2025-11-08T11:23:32Z",
            "repository": {
                "owner": "test",
                "name": "repo",
                "url": "https://github.com/test/repo",
            },
            "branch": "main",
            "commit": {"sha": "abc123def456", "author": "user", "message": "msg"},
            "tier": "pro",
            "status": "invalid_status",  # Should be pass/fail/partial
            "scores": {"overall": 85, "categories": {}},
            "gates": {"executed": [], "summary": {}},
            "cache_metrics": {},
            "security": {},
            "compliance": {},
        }
        is_valid, errors = validate_audit_report(invalid_report)
        assert is_valid is False

    def test_validate_audit_report_fails_for_invalid_tier(self):
        """Invalid tier should fail validation."""
        invalid_report = {
            "version": "1.0.0",
            "timestamp": "2025-11-08T11:23:32Z",
            "repository": {
                "owner": "test",
                "name": "repo",
                "url": "https://github.com/test/repo",
            },
            "branch": "main",
            "commit": {"sha": "abc123def456", "author": "user", "message": "msg"},
            "tier": "invalid_tier",  # Should be lite/pro/strict/promax
            "status": "pass",
            "scores": {"overall": 85, "categories": {}},
            "gates": {"executed": [], "summary": {}},
            "cache_metrics": {},
            "security": {},
            "compliance": {},
        }
        is_valid, errors = validate_audit_report(invalid_report)
        assert is_valid is False


class TestAuditReportEmission:
    """Tests for emitting audit reports to files."""

    @pytest.fixture
    def sample_report(self):
        """Sample audit report for testing."""
        return emit_audit_report(
            overall_score=85,
            category_scores={
                "architecture": 90,
                "security": 95,
                "performance": 88,
                "test_coverage": 75,
                "enforcement": 80,
                "ci_parity": 85,
            },
            gates_executed=[
                {
                    "name": "ruff",
                    "status": "pass",
                    "duration_ms": 500,
                    "exit_code": 0,
                }
            ],
            repository={
                "owner": "test",
                "name": "repo",
                "url": "https://github.com/test/repo",
            },
            branch="main",
            commit_info={"sha": "abc123def456", "author": "user", "message": "msg"},
            tier="pro",
        )

    def test_emit_audit_json_creates_file(self, sample_report):
        """emit_audit_json should create a JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "audit.json"
            emit_audit_json(sample_report, output_path)
            assert output_path.exists()
            assert output_path.stat().st_size > 0

    def test_emit_audit_json_valid_content(self, sample_report):
        """JSON file should contain valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "audit.json"
            emit_audit_json(sample_report, output_path)
            with open(output_path) as f:
                data = json.load(f)
            assert data["version"] == "1.0.0"
            assert data["status"] == "pass"

    def test_emit_audit_json_creates_parent_directories(self):
        """emit_audit_json should create parent directories if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dirs" / "audit.json"
            sample_report = emit_audit_report(
                overall_score=85,
                category_scores={"architecture": 90},
                gates_executed=[],
                repository={"owner": "test", "name": "repo", "url": "https://test"},
                branch="main",
                commit_info={"sha": "abc123def456", "author": "u", "message": "m"},
                tier="lite",
            )
            emit_audit_json(sample_report, output_path)
            assert output_path.exists()

    def test_emit_audit_summary_creates_file(self, sample_report):
        """emit_audit_summary should create a text file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "audit_summary.txt"
            emit_audit_summary(sample_report, output_path)
            assert output_path.exists()
            assert output_path.stat().st_size > 0

    def test_emit_audit_summary_readable_content(self, sample_report):
        """Summary file should contain readable audit information."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "audit_summary.txt"
            emit_audit_summary(sample_report, output_path)
            with open(output_path) as f:
                content = f.read()
            assert "FirstTry Audit Report" in content
            assert "Repository: repo" in content
            assert "Overall Score: 85/100" in content
            assert "Status: PASS" in content

    def test_emit_audit_summary_includes_categories(self, sample_report):
        """Summary should include all category scores."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "audit_summary.txt"
            emit_audit_summary(sample_report, output_path)
            with open(output_path) as f:
                content = f.read()
            assert "architecture" in content
            assert "security" in content
            assert "performance" in content


class TestAuditReportEdgeCases:
    """Tests for edge cases and error handling."""

    def test_emit_audit_report_with_zero_gates(self):
        """Should handle reports with no gates executed."""
        report = emit_audit_report(
            overall_score=50,
            category_scores={"architecture": 50},
            gates_executed=[],
            repository={"owner": "test", "name": "repo", "url": "https://test"},
            branch="main",
            commit_info={"sha": "abc123def456", "author": "u", "message": "m"},
            tier="lite",
        )
        assert report["gates"]["summary"]["total"] == 0
        assert report["status"] == "pass"

    def test_emit_audit_report_with_max_scores(self):
        """Should handle perfect scores (100/100)."""
        report = emit_audit_report(
            overall_score=100,
            category_scores={
                "architecture": 100,
                "security": 100,
                "performance": 100,
            },
            gates_executed=[{"name": "ruff", "status": "pass", "duration_ms": 100}],
            repository={"owner": "test", "name": "repo", "url": "https://test"},
            branch="main",
            commit_info={"sha": "abc123def456", "author": "u", "message": "m"},
            tier="promax",
        )
        assert report["scores"]["overall"] == 100
        assert report["status"] == "pass"

    def test_emit_audit_report_with_minimum_scores(self):
        """Should handle zero scores."""
        report = emit_audit_report(
            overall_score=0,
            category_scores={"architecture": 0},
            gates_executed=[
                {
                    "name": "ruff",
                    "status": "fail",
                    "duration_ms": 100,
                    "exit_code": 1,
                }
            ],
            repository={"owner": "test", "name": "repo", "url": "https://test"},
            branch="main",
            commit_info={"sha": "abc123def456", "author": "u", "message": "m"},
            tier="lite",
        )
        assert report["scores"]["overall"] == 0
        assert report["status"] == "fail"

    def test_emit_audit_report_with_long_gate_list(self):
        """Should handle reports with many gates."""
        gates = [
            {
                "name": f"gate_{i}",
                "status": "pass" if i % 2 == 0 else "fail",
                "duration_ms": 100 * i,
            }
            for i in range(50)
        ]
        report = emit_audit_report(
            overall_score=50,
            category_scores={"architecture": 50},
            gates_executed=gates,
            repository={"owner": "test", "name": "repo", "url": "https://test"},
            branch="main",
            commit_info={"sha": "abc123def456", "author": "u", "message": "m"},
            tier="pro",
        )
        assert len(report["gates"]["executed"]) == 50
        assert report["gates"]["summary"]["total"] == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
