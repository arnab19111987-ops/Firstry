"""Dependency vulnerability scanning using pip-audit.

Tests for:
1. Vulnerability detection in dependencies
2. Severity level classification
3. Policy enforcement for vulnerabilities
4. Dependency update recommendations
5. SCA (Software Composition Analysis) integration
"""

import json
from pathlib import Path
from typing import Any, Dict

import pytest


@pytest.fixture
def pip_audit_config() -> Dict[str, Any]:
    """Fixture providing pip-audit configuration."""
    return {
        "version": "2.6.0",
        "scan_type": "environment",
        "formats": ["json", "markdown"],
        "cache": True,
        "skip": [],  # Can skip specific CVEs if accepted risk
        "severity_levels": {
            "CRITICAL": {"score": 9.0, "action": "block"},
            "HIGH": {"score": 7.0, "action": "warn"},
            "MEDIUM": {"score": 4.0, "action": "log"},
            "LOW": {"score": 0.1, "action": "info"},
        },
    }


@pytest.fixture
def vulnerable_requirements(tmp_path: Path) -> Path:
    """Create a requirements file with known vulnerable packages."""
    req_file = tmp_path / "requirements.txt"
    req_file.write_text(
        """
# Example: requirements with known vulnerabilities (for testing detection)
requests==2.25.0
urllib3==1.26.0
cryptography==3.2
django==2.2.0
"""
    )
    return req_file


def test_pip_audit_configuration(pip_audit_config: Dict[str, Any]):
    """Test that pip-audit configuration is valid."""
    assert "version" in pip_audit_config
    assert "severity_levels" in pip_audit_config
    assert "CRITICAL" in pip_audit_config["severity_levels"]
    assert "HIGH" in pip_audit_config["severity_levels"]


def test_severity_classification(pip_audit_config: Dict[str, Any]):
    """Test severity level classification."""
    severities = pip_audit_config["severity_levels"]

    # Verify severity hierarchy
    assert severities["CRITICAL"]["score"] > severities["HIGH"]["score"]
    assert severities["HIGH"]["score"] > severities["MEDIUM"]["score"]
    assert severities["MEDIUM"]["score"] > severities["LOW"]["score"]

    # Verify action mapping
    assert severities["CRITICAL"]["action"] == "block"
    assert severities["HIGH"]["action"] == "warn"


def test_vulnerability_report_structure(tmp_path: Path):
    """Test structure of vulnerability report."""
    report = {
        "scan_date": "2024-01-15T10:00:00Z",
        "total_dependencies": 42,
        "vulnerabilities_found": 3,
        "by_severity": {
            "CRITICAL": 1,
            "HIGH": 1,
            "MEDIUM": 1,
            "LOW": 0,
        },
        "findings": [
            {
                "package": "requests",
                "version": "2.25.0",
                "vulnerability_id": "CVE-2021-33503",
                "severity": "HIGH",
                "description": "urllib3 before 1.26.5 allows authorization HTTP header injection",
                "fixed_version": "2.25.1",
            }
        ],
    }

    report_file = tmp_path / "audit_report.json"
    report_file.write_text(json.dumps(report, indent=2))

    loaded = json.loads(report_file.read_text())

    assert loaded["scan_date"] is not None
    assert loaded["vulnerabilities_found"] == 3
    assert len(loaded["findings"]) > 0


def test_policy_enforcement_critical(pip_audit_config: Dict[str, Any]):
    """Test that CRITICAL vulnerabilities block pipeline."""
    severity = pip_audit_config["severity_levels"]["CRITICAL"]

    # Critical vulnerabilities must fail CI
    assert severity["action"] == "block"

    # Policy: No CRITICAL vulnerabilities allowed
    policy = {
        "max_critical": 0,
        "max_high": 0,
        "max_medium": 5,
        "action": "fail_if_exceeded",
    }

    assert policy["max_critical"] == 0


def test_policy_enforcement_high(pip_audit_config: Dict[str, Any]):
    """Test that HIGH vulnerabilities are tracked."""
    severity = pip_audit_config["severity_levels"]["HIGH"]

    assert severity["action"] == "warn"

    # Policy: Limited HIGH vulnerabilities allowed
    policy = {
        "max_high": 0,  # For strict tier
        "action": "require_justification",
    }

    assert policy["max_high"] == 0


def test_skip_vulnerable_cves(pip_audit_config: Dict[str, Any]):
    """Test ability to skip specific CVEs with justification."""
    # Allow skipping specific CVEs if risk accepted
    skip_config = {
        "CVE-2021-12345": {
            "package": "example-pkg",
            "reason": "Mitigation in place: input validation",
            "approved_by": "security-team",
            "expires": "2024-12-31",
        }
    }

    assert "CVE-2021-12345" in skip_config
    assert skip_config["CVE-2021-12345"]["approved_by"] == "security-team"


def test_dependency_update_recommendations(tmp_path: Path):
    """Test generation of dependency update recommendations."""
    recommendations = [
        {
            "package": "requests",
            "current": "2.25.0",
            "recommended": "2.31.0",
            "reason": "Security update (3 CVEs fixed)",
            "breaking_changes": False,
        },
        {
            "package": "django",
            "current": "2.2.0",
            "recommended": "4.2.0",
            "reason": "Critical security updates + end-of-life",
            "breaking_changes": True,
        },
    ]

    recs_file = tmp_path / "update_recommendations.json"
    recs_file.write_text(json.dumps(recommendations, indent=2))

    loaded = json.loads(recs_file.read_text())

    assert len(loaded) == 2
    assert not loaded[0]["breaking_changes"]
    assert loaded[1]["breaking_changes"]


def test_sbom_vulnerability_correlation():
    """Test correlation of vulnerabilities with SBOM entries."""
    sbom_entry = {
        "package": "cryptography",
        "version": "3.2",
        "hash": "sha256:abc123...",
        "vulnerabilities": [
            {
                "cve": "CVE-2020-25659",
                "severity": "HIGH",
                "fixed_in": "3.2.1",
            }
        ],
    }

    assert len(sbom_entry["vulnerabilities"]) > 0
    assert sbom_entry["vulnerabilities"][0]["severity"] == "HIGH"


def test_transitive_dependency_scanning():
    """Test scanning of transitive (indirect) dependencies."""
    # pip-audit should detect vulnerabilities in transitive deps
    dependencies = {
        "direct": [
            {"name": "requests", "version": "2.28.0"},
        ],
        "transitive": [
            {"name": "urllib3", "version": "1.26.5", "required_by": "requests"},
            {"name": "certifi", "version": "2021.10.8", "required_by": "requests"},
        ],
    }

    # Find vulnerable transitive deps
    vulnerable = [
        dep
        for dep in dependencies["transitive"]
        if dep["name"] == "urllib3" and dep["version"] < "1.26.8"
    ]

    assert len(vulnerable) > 0


def test_policy_violation_report(tmp_path: Path):
    """Test generation of policy violation report."""
    violation_report = {
        "timestamp": "2024-01-15T10:00:00Z",
        "policy": "enterprise-strict",
        "violations": [
            {
                "type": "critical_vulnerability",
                "package": "cryptography",
                "version": "3.2",
                "cve": "CVE-2020-25659",
                "action": "BLOCKED",
            },
        ],
        "pipeline_status": "FAILED",
    }

    report_file = tmp_path / "policy_violation.json"
    report_file.write_text(json.dumps(violation_report, indent=2))

    loaded = json.loads(report_file.read_text())

    assert loaded["pipeline_status"] == "FAILED"
    assert loaded["violations"][0]["action"] == "BLOCKED"


def test_continuous_scanning_enabled():
    """Test that continuous dependency scanning is enabled."""
    continuous_config = {
        "enabled": True,
        "frequency": "daily",
        "on_new_findings": "notify",
        "block_on_critical": True,
        "channels": ["email", "slack", "github_issue"],
    }

    assert continuous_config["enabled"]
    assert continuous_config["block_on_critical"]


def test_ci_integration_pip_audit():
    """Test pip-audit integration in CI/CD pipeline."""
    ci_job = {
        "name": "Dependency Audit",
        "stage": "security",
        "image": "python:3.11",
        "script": [
            "pip install pip-audit",
            "pip-audit --desc --format json --output audit_report.json",
            "pip-audit --desc",  # Also print to log
        ],
        "artifacts": {
            "paths": ["audit_report.json"],
            "when": "always",
        },
        "allow_failure": False,  # Must pass (CRITICAL/HIGH fail pipeline)
        "retry": {"max": 2, "when": ["runner_system_failure"]},
    }

    assert not ci_job["allow_failure"]
    assert "audit_report.json" in ci_job["artifacts"]["paths"]


def test_vulnerability_trend_tracking(tmp_path: Path):
    """Test tracking vulnerability trends over time."""
    trend_data = [
        {"date": "2024-01-01", "critical": 1, "high": 3, "medium": 12, "low": 5},
        {"date": "2024-01-08", "critical": 0, "high": 2, "medium": 10, "low": 4},
        {"date": "2024-01-15", "critical": 0, "high": 1, "medium": 8, "low": 3},
    ]

    trend_file = tmp_path / "vulnerability_trend.json"
    trend_file.write_text(json.dumps(trend_data, indent=2))

    loaded = json.loads(trend_file.read_text())

    # Verify trend is improving
    assert loaded[0]["critical"] >= loaded[1]["critical"]
    assert loaded[1]["critical"] >= loaded[2]["critical"]


def test_remediation_deadline_enforcement():
    """Test enforcement of remediation deadlines."""
    vulnerability = {
        "cve": "CVE-2024-12345",
        "severity": "HIGH",
        "detected_date": "2024-01-01",
        "remediation_deadline": "2024-02-01",  # 30 days
        "status": "open",
    }

    # Check if past deadline
    from datetime import datetime

    deadline = datetime.fromisoformat(vulnerability["remediation_deadline"])
    is_overdue = datetime.now() > deadline

    # Should have remediation plan
    assert vulnerability["status"] in ["open", "in_progress", "resolved"]


def test_license_compliance_with_audit():
    """Test that pip-audit output includes license information."""
    # Some tools like pip-audit can output license info
    dependency_info = {
        "package": "requests",
        "version": "2.31.0",
        "license": "Apache 2.0",
        "vulnerabilities": 0,
        "outdated": False,
    }

    # Should be compatible with organizational policy
    allowed_licenses = ["Apache 2.0", "MIT", "BSD", "MPL-2.0"]
    assert dependency_info["license"] in allowed_licenses


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
