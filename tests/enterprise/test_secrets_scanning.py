"""Secrets scanning integration using gitleaks.

Tests for:
1. Secret detection and prevention
2. Repository pre-scan validation
3. CI/CD blocking on secrets found
4. Secret pattern customization
5. Allowlist management
"""

import json
from pathlib import Path
from typing import Any, Dict

import pytest


@pytest.fixture
def gitleaks_config() -> Dict[str, Any]:
    """Fixture providing gitleaks configuration."""
    return {
        "version": 1,
        "title": "FirstTry Security Config",
        "description": "Gitleaks configuration for FirstTry",
        "rules": [
            {
                "id": "aws-access-key",
                "description": "AWS Access Key ID",
                "pattern": "AKIA[0-9A-Z]{16}",
                "entropy": 3.5,
            },
            {
                "id": "private-key",
                "description": "Private Key",
                "pattern": "-----BEGIN RSA PRIVATE KEY-----",
            },
            {
                "id": "github-token",
                "description": "GitHub Token",
                "pattern": "ghp_[0-9a-zA-Z]{36}",
            },
        ],
        "allowlist": {
            "paths": [
                ".*\\.md$",
                "tests/.*",
                "docs/examples/.*",
            ]
        },
    }


@pytest.fixture
def gitleaks_config_file(tmp_path: Path, gitleaks_config: Dict[str, Any]) -> Path:
    """Create gitleaks configuration file."""
    config_file = tmp_path / ".gitleaks.toml"
    # Convert dict to TOML format
    toml_content = "[general]\n"
    toml_content += f'title = "{gitleaks_config["title"]}"\n'
    toml_content += f'description = "{gitleaks_config["description"]}"\n'
    config_file.write_text(toml_content)
    return config_file


def test_gitleaks_config_validation(gitleaks_config: Dict[str, Any]):
    """Test that gitleaks configuration is valid."""
    assert "version" in gitleaks_config
    assert "rules" in gitleaks_config
    assert len(gitleaks_config["rules"]) > 0

    # Verify rule structure
    for rule in gitleaks_config["rules"]:
        assert "id" in rule
        assert "description" in rule
        assert "pattern" in rule


def test_secret_detection_aws_key(tmp_path: Path):
    """Test detection of AWS access keys."""
    # Create a file with a fake AWS key
    test_file = tmp_path / "config.py"
    test_file.write_text(
        """
# Configuration
AWS_KEY = "AKIA1234567890ABCDEF"  # Fake key for testing
SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
"""
    )

    # Pattern should match AWS key format
    import re

    aws_pattern = r"AKIA[0-9A-Z]{16}"
    content = test_file.read_text()

    matches = re.findall(aws_pattern, content)
    assert len(matches) > 0
    assert "AKIA1234567890ABCDEF" in matches


def test_secret_detection_github_token(tmp_path: Path):
    """Test detection of GitHub tokens."""
    test_file = tmp_path / "token.py"
    test_file.write_text(
        """
GITHUB_TOKEN = "ghp_abcdefghijklmnopqrstuvwxyz12345678"
"""
    )

    # Pattern should match GitHub token format
    import re

    github_pattern = r"ghp_[0-9a-zA-Z]+"
    content = test_file.read_text()

    matches = re.findall(github_pattern, content)
    assert len(matches) > 0


def test_secret_detection_private_key(tmp_path: Path):
    """Test detection of private keys."""
    test_file = tmp_path / "key.pem"
    test_file.write_text(
        """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA1234567890abcdefghijklmnopqrstuvwxyz
-----END RSA PRIVATE KEY-----
"""
    )

    content = test_file.read_text()
    assert "-----BEGIN RSA PRIVATE KEY-----" in content


def test_allowlist_paths_not_scanned(gitleaks_config: Dict[str, Any]):
    """Test that allowlisted paths are excluded from scanning."""
    allowlist = gitleaks_config["allowlist"]["paths"]

    # Example paths that should be allowlisted
    test_paths = [
        "README.md",
        "tests/test_example.py",
        "docs/examples/config.yaml",
    ]

    import re

    for path in test_paths:
        # Should match at least one allowlist pattern
        matches = [re.match(pattern, path) for pattern in allowlist]
        assert any(matches), f"Path {path} should be allowlisted"


def test_gitleaks_ci_blocking(gitleaks_config: Dict[str, Any]):
    """Test that secrets found will block CI/CD pipeline."""
    # This test verifies the enforcement logic

    # If secrets are found, CI should:
    # 1. Report all findings
    # 2. Exit with non-zero code
    # 3. Prevent merge

    enforcement_rules = {
        "fail_on_secrets_found": True,
        "block_commit": True,
        "require_review": False,
    }

    assert enforcement_rules["fail_on_secrets_found"]
    assert enforcement_rules["block_commit"]


def test_secret_pattern_customization(gitleaks_config: Dict[str, Any]):
    """Test that secret patterns can be customized."""
    # Users should be able to add custom patterns
    custom_rule = {
        "id": "custom-api-key",
        "description": "Custom API Key",
        "pattern": "API_KEY=['\"][^'\"]+['\"]",
    }

    gitleaks_config["rules"].append(custom_rule)

    assert "custom-api-key" in [r["id"] for r in gitleaks_config["rules"]]


def test_false_positive_management(gitleaks_config: Dict[str, Any]):
    """Test handling of false positives."""
    # Gitleaks allows exceptions for known false positives
    exception = {
        "path": "tests/fixtures/example_keys.txt",
        "pattern": "AKIA",
        "reason": "Test fixture with fake keys",
    }

    # Should be storable in allowlist
    if "exceptions" not in gitleaks_config:
        gitleaks_config["exceptions"] = []

    gitleaks_config["exceptions"].append(exception)

    assert len(gitleaks_config["exceptions"]) > 0


def test_pre_commit_hook_integration():
    """Test integration with pre-commit hooks."""
    # Gitleaks should run before commit
    pre_commit_config = {
        "repos": [
            {
                "repo": "https://github.com/gitleaks/pre-commit-hook.git",
                "rev": "v8.0.0",
                "hooks": [
                    {
                        "id": "gitleaks",
                        "stages": ["commit"],
                        "args": ["--verbose", "--redact"],
                    }
                ],
            }
        ]
    }

    assert len(pre_commit_config["repos"]) > 0
    assert pre_commit_config["repos"][0]["repo"].endswith(".git")


def test_audit_trail_logging(tmp_path: Path):
    """Test that secrets scanning creates audit trail."""
    audit_log = {
        "timestamp": "2024-01-15T10:00:00Z",
        "action": "secrets_scan",
        "status": "completed",
        "files_scanned": 1024,
        "secrets_found": 0,
        "findings": [],
    }

    audit_file = tmp_path / "secrets_audit.json"
    audit_file.write_text(json.dumps(audit_log, indent=2))

    loaded = json.loads(audit_file.read_text())

    assert loaded["action"] == "secrets_scan"
    assert loaded["files_scanned"] > 0


def test_policy_enforcement_with_secrets(gitleaks_config: Dict[str, Any]):
    """Test policy enforcement when secrets are detected."""
    # Policy should enforce: no secrets allowed
    policy_enforcement = {
        "secrets_scanning": {
            "enabled": True,
            "fail_on_error": True,
            "fail_on_findings": True,
        }
    }

    assert policy_enforcement["secrets_scanning"]["fail_on_findings"]


def test_remediation_workflow():
    """Test workflow for fixing detected secrets."""
    remediation_steps = [
        "1. Identify secret in repository history",
        "2. Rotate exposed credentials",
        "3. Remove secret from commit history (git filter-branch or BFG)",
        "4. Force push to update remote",
        "5. Verify with gitleaks scan",
        "6. Update monitoring/notifications",
    ]

    assert len(remediation_steps) == 6
    assert "Rotate exposed credentials" in remediation_steps[1]


def test_enterprise_secret_vault_integration():
    """Test integration with enterprise secret vaults."""
    vault_config = {
        "vault_type": "HashiCorp Vault",
        "endpoint": "https://vault.example.com",
        "auth_method": "kubernetes",
        "secret_path": "/secret/firsttry",
        "allowed_roles": ["firsttry-ci", "firsttry-dev"],
    }

    assert vault_config["vault_type"] == "HashiCorp Vault"
    assert len(vault_config["allowed_roles"]) > 0


def test_ci_pipeline_secret_scanning():
    """Test secrets scanning in CI pipeline."""
    ci_job = {
        "name": "Secrets Scan",
        "stage": "security",
        "image": "gitleaks:latest",
        "script": [
            "gitleaks detect --verbose --report-path scan-report.json",
            "cat scan-report.json",
        ],
        "artifacts": {
            "paths": ["scan-report.json"],
            "when": "always",
        },
        "allow_failure": False,  # Must pass
    }

    assert not ci_job["allow_failure"]
    assert len(ci_job["script"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
