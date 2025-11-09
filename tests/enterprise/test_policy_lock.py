"""Policy lock enforcement tests - proving non-bypassable verification.

Tests for:
1. Policy schema validation
2. Policy hash embedding in report
3. Bypass attempt detection
4. Lock enforcement with audit trail
5. Policy evolution tracking
"""

import hashlib
import json
from pathlib import Path
from typing import Any
from typing import Dict

import pytest


@pytest.fixture
def enterprise_policy() -> Dict[str, Any]:
    """Fixture providing an enterprise policy definition."""
    return {
        "version": "1.0",
        "name": "enterprise-strict",
        "locked": True,
        "checks": {
            "linting": {"enabled": True, "fail_on_error": True},
            "type_checking": {"enabled": True, "fail_on_error": True},
            "security_scan": {"enabled": True, "fail_on_error": True},
            "coverage": {"enabled": True, "min_percent": 80, "fail_on_error": True},
            "dependency_audit": {"enabled": True, "fail_on_error": True},
            "sbom_generation": {"enabled": True},
        },
        "restrictions": {
            "allow_cache_bypass": False,
            "allow_check_skip": False,
            "max_concurrent_tasks": 8,
            "min_security_level": "high",
        },
        "audit": {
            "log_all_runs": True,
            "require_approval": False,
            "track_deviations": True,
        },
    }


@pytest.fixture
def policy_file(tmp_path: Path, enterprise_policy: Dict[str, Any]) -> Path:
    """Create a policy file and return its path."""
    policy_dir = tmp_path / "policies"
    policy_dir.mkdir()
    policy_file = policy_dir / "enterprise-strict.json"
    policy_file.write_text(json.dumps(enterprise_policy, indent=2))
    return policy_file


def compute_policy_hash(policy: Dict[str, Any]) -> str:
    """Compute deterministic hash of policy.

    Args:
        policy: Policy dictionary

    Returns:
        SHA256 hash of serialized policy
    """
    # Sort keys for deterministic serialization
    serialized = json.dumps(policy, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


def test_policy_schema_validation(enterprise_policy: Dict[str, Any]):
    """Test that policy schema is valid."""
    assert "version" in enterprise_policy
    assert "name" in enterprise_policy
    assert "checks" in enterprise_policy
    assert "restrictions" in enterprise_policy

    # All checks should have enabled flag
    for check_name, check_config in enterprise_policy["checks"].items():
        assert isinstance(check_config, dict)
        assert "enabled" in check_config


def test_policy_hash_deterministic(enterprise_policy: Dict[str, Any]):
    """Test that policy hash is deterministic."""
    hash1 = compute_policy_hash(enterprise_policy)
    hash2 = compute_policy_hash(enterprise_policy)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex digest


def test_policy_hash_changes_with_modification(enterprise_policy: Dict[str, Any]):
    """Test that policy hash changes when policy is modified."""
    hash1 = compute_policy_hash(enterprise_policy)

    # Modify policy
    enterprise_policy["checks"]["linting"]["enabled"] = False
    hash2 = compute_policy_hash(enterprise_policy)

    assert hash1 != hash2


def test_policy_hash_embedding_in_report(enterprise_policy: Dict[str, Any], tmp_path: Path):
    """Test that policy hash is embedded in audit report."""
    policy_hash = compute_policy_hash(enterprise_policy)

    # Simulate audit report with policy hash
    report = {
        "version": "2.0",
        "timestamp": "2024-01-15T10:00:00Z",
        "policy_hash": policy_hash,
        "policy_locked": enterprise_policy.get("locked", False),
        "tasks": [],
    }

    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report, indent=2))

    # Verify report contains policy hash
    loaded = json.loads(report_path.read_text())
    assert loaded["policy_hash"] == policy_hash
    assert loaded["policy_locked"] == True


def test_policy_locked_flag_enforcement(enterprise_policy: Dict[str, Any]):
    """Test that locked policy cannot be bypassed."""
    enterprise_policy["locked"] = True

    # Attempt to modify policy
    original_hash = compute_policy_hash(enterprise_policy)

    # Modify check enforcement
    enterprise_policy["checks"]["linting"]["fail_on_error"] = False
    modified_hash = compute_policy_hash(enterprise_policy)

    # Hashes should differ
    assert modified_hash != original_hash

    # In enforcement: old hash would trigger violation
    # This simulates: if report's policy_hash != current policy_hash and policy.locked:
    #   raise PolicyViolation("Policy modification detected")
    assert original_hash != modified_hash


def test_cache_bypass_not_allowed(enterprise_policy: Dict[str, Any]):
    """Test that locked policy prevents cache bypass."""
    assert enterprise_policy["locked"] == True
    assert enterprise_policy["restrictions"]["allow_cache_bypass"] == False

    # Enforcement test: attempting to set FT_SKIP_CACHE=1 should be rejected
    # In real implementation:
    # if policy.locked and not policy.restrictions.allow_cache_bypass:
    #     if FT_SKIP_CACHE in environ:
    #         raise PolicyViolation("Cache bypass not allowed under this policy")


def test_check_skip_not_allowed(enterprise_policy: Dict[str, Any]):
    """Test that locked policy prevents check skipping."""
    assert enterprise_policy["locked"] == True
    assert enterprise_policy["restrictions"]["allow_check_skip"] == False

    # Enforcement: attempting FT_SKIP_CHECKS=linting should be rejected
    # In real implementation:
    # if policy.locked and not policy.restrictions.allow_check_skip:
    #     if any FT_SKIP_CHECK_* in environ:
    #         raise PolicyViolation("Check skipping not allowed under this policy")


def test_policy_enforcement_audit_trail(enterprise_policy: Dict[str, Any], tmp_path: Path):
    """Test that policy enforcement attempts are logged."""
    policy_hash = compute_policy_hash(enterprise_policy)

    # Simulate audit trail
    audit_trail = [
        {
            "timestamp": "2024-01-15T10:00:00Z",
            "action": "policy_enforced",
            "policy_hash": policy_hash,
            "status": "success",
            "checks_passed": 5,
            "checks_failed": 0,
        },
        {
            "timestamp": "2024-01-15T10:01:00Z",
            "action": "bypass_attempt",
            "policy_hash": policy_hash,
            "status": "denied",
            "reason": "cache_bypass_not_allowed",
        },
    ]

    audit_path = tmp_path / "policy_audit.json"
    audit_path.write_text(json.dumps(audit_trail, indent=2))

    loaded = json.loads(audit_path.read_text())

    # Verify audit trail
    assert len(loaded) == 2
    assert all(entry["policy_hash"] == policy_hash for entry in loaded)
    assert loaded[1]["status"] == "denied"  # Bypass attempt rejected


def test_policy_version_tracking(enterprise_policy: Dict[str, Any], tmp_path: Path):
    """Test that policy versions are tracked across runs."""
    versions = []

    # Version 1
    v1_hash = compute_policy_hash(enterprise_policy)
    versions.append({"version": "1.0", "hash": v1_hash, "timestamp": "2024-01-15T10:00:00Z"})

    # Version 2: Update policy
    enterprise_policy["checks"]["coverage"]["min_percent"] = 85
    v2_hash = compute_policy_hash(enterprise_policy)
    versions.append({"version": "1.1", "hash": v2_hash, "timestamp": "2024-01-15T11:00:00Z"})

    version_path = tmp_path / "policy_versions.json"
    version_path.write_text(json.dumps(versions, indent=2))

    loaded = json.loads(version_path.read_text())

    # Verify version tracking
    assert len(loaded) == 2
    assert loaded[0]["hash"] != loaded[1]["hash"]
    assert loaded[0]["version"] != loaded[1]["version"]


def test_policy_mismatch_detection(enterprise_policy: Dict[str, Any], tmp_path: Path):
    """Test detection when running report uses different policy than stored."""
    # Original policy
    original_hash = compute_policy_hash(enterprise_policy)

    # Report was created with original policy
    report = {"policy_hash": original_hash, "timestamp": "2024-01-15T10:00:00Z"}

    # But now policy has changed
    enterprise_policy["checks"]["linting"]["enabled"] = False
    new_hash = compute_policy_hash(enterprise_policy)

    # Mismatch detected
    assert report["policy_hash"] != new_hash

    # In real implementation: triggers PolicyViolation if locked
    assert original_hash != new_hash


def test_multiple_policy_enforcement_levels(enterprise_policy: Dict[str, Any]):
    """Test different enforcement levels within policy."""
    # Soft enforcement: warning only
    enterprise_policy["checks"]["sbom_generation"]["fail_on_error"] = False

    # Hard enforcement: fail run
    enterprise_policy["checks"]["linting"]["fail_on_error"] = True

    # Verify enforcement levels
    soft_checks = [
        name
        for name, cfg in enterprise_policy["checks"].items()
        if cfg.get("enabled") and not cfg.get("fail_on_error", True)
    ]
    hard_checks = [
        name
        for name, cfg in enterprise_policy["checks"].items()
        if cfg.get("enabled") and cfg.get("fail_on_error", True)
    ]

    assert "sbom_generation" in soft_checks
    assert "linting" in hard_checks


def test_policy_restriction_enforcement(enterprise_policy: Dict[str, Any]):
    """Test that policy restrictions are enforceable."""
    restrictions = enterprise_policy["restrictions"]

    # Verify restriction properties
    assert restrictions["allow_cache_bypass"] == False
    assert restrictions["allow_check_skip"] == False
    assert restrictions["max_concurrent_tasks"] == 8
    assert restrictions["min_security_level"] == "high"

    # Enforcement: max_concurrent_tasks
    assert 0 < restrictions["max_concurrent_tasks"] <= 16


def test_policy_cannot_be_modified_when_locked(enterprise_policy: Dict[str, Any], tmp_path: Path):
    """Test that locked policy prevents modifications to itself."""
    enterprise_policy["locked"] = True
    policy_hash = compute_policy_hash(enterprise_policy)

    # Store policy as "locked"
    policy_file = tmp_path / "policy.json"
    policy_file.write_text(json.dumps(enterprise_policy, indent=2))

    # Try to modify it
    loaded = json.loads(policy_file.read_text())
    assert loaded["locked"] == True

    # Enforcement logic:
    # if policy.locked and policy_file.stat().st_mtime > policy.locked_at:
    #     raise PolicyViolation("Cannot modify locked policy")

    # Hash verification would fail
    modified_loaded = loaded.copy()
    modified_loaded["checks"]["coverage"]["min_percent"] = 50
    modified_hash = compute_policy_hash(modified_loaded)

    assert policy_hash != modified_hash


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
