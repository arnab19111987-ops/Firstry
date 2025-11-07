#!/usr/bin/env python3
"""
demo_license_examples.py

Practical examples of using the demo license key in tests and development.
"""

import os
from pathlib import Path

# Add src to path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 70)
print("Demo License Examples")
print("=" * 70)

# ============================================================================
# Example 1: Direct environment setup
# ============================================================================
print("\n[Example 1] Direct Environment Setup")
print("-" * 70)

os.environ["FIRSTTRY_LICENSE_KEY"] = "demo-lic-key-2025"
os.environ["FIRSTTRY_TIER"] = "pro"
os.environ["FIRSTTRY_LICENSE_BACKEND"] = "env"
os.environ["FIRSTTRY_LICENSE_ALLOW"] = "pro,promax"

from firsttry import license_guard

print(f"Current tier: {license_guard.get_tier()}")
print(f"Is pro? {license_guard.is_pro()}")
print(f"Is free? {license_guard.is_free_tier()}")
print(f"Is paid? {license_guard.is_paid_tier()}")

try:
    license_guard.ensure_license_for_current_tier()
    print("✓ License validation: PASSED")
except license_guard.LicenseError as e:
    print(f"✗ License validation: FAILED - {e}")

# ============================================================================
# Example 2: Using DemoLicense class
# ============================================================================
print("\n[Example 2] Using DemoLicense Class")
print("-" * 70)

from demo_license_for_tests import DemoLicense

# Create demo license for pro tier
demo = DemoLicense(tier="pro")
demo.enable()

print(f"Demo license enabled: {demo}")
print(f"Tier: {license_guard.get_tier()}")
print(f"Is pro? {license_guard.is_pro()}")

demo.disable()
print("Demo license disabled")

# ============================================================================
# Example 3: Using context manager
# ============================================================================
print("\n[Example 3] Context Manager Usage")
print("-" * 70)

print("Before context: FIRSTTRY_TIER not set")
print(f"  Tier: {license_guard.get_tier()}")

with DemoLicense(tier="pro"):
    print("Inside context: demo license active")
    print(f"  Tier: {license_guard.get_tier()}")
    print(f"  Is pro? {license_guard.is_pro()}")

print("After context: demo license restored")
print(f"  Tier: {license_guard.get_tier()}")

# ============================================================================
# Example 4: Testing different tiers
# ============================================================================
print("\n[Example 4] Testing Different Tiers")
print("-" * 70)

for tier_name in ["pro", "promax", "free-lite", "free-strict"]:
    with DemoLicense(tier=tier_name):
        actual_tier = license_guard.get_tier()
        is_free = license_guard.is_free_tier()
        is_paid = license_guard.is_paid_tier()
        print(f"  {tier_name:12} → {actual_tier:12} (free={is_free}, paid={is_paid})")

# ============================================================================
# Example 5: Simulating pytest fixtures
# ============================================================================
print("\n[Example 5] Simulating pytest Fixtures")
print("-" * 70)


def fixture_with_pro_license():
    """Example pytest fixture."""
    license_mgr = DemoLicense(tier="pro")
    license_mgr.enable()
    yield license_mgr
    license_mgr.disable()


def test_example_with_license(fixture_mgr=None):
    """Example test using fixture."""
    # In real pytest, this would be injected
    fixture_mgr = fixture_with_pro_license()
    next(fixture_mgr)  # Enable

    try:
        print(f"  ✓ Test running with tier: {license_guard.get_tier()}")
        print(f"  ✓ License key: {os.getenv('FIRSTTRY_LICENSE_KEY')}")
        print(f"  ✓ Backend: {os.getenv('FIRSTTRY_LICENSE_BACKEND')}")
    finally:
        next(fixture_mgr, None)  # Cleanup


test_example_with_license()

# ============================================================================
# Example 6: Batch testing multiple features
# ============================================================================
print("\n[Example 6] Batch Testing Multiple Features")
print("-" * 70)

features_to_test = [
    ("Pro tier capability", "pro"),
    ("ProMax tier capability", "promax"),
    ("Free tier capability", "free-lite"),
]

for feature_name, tier in features_to_test:
    with DemoLicense(tier=tier):
        try:
            license_guard.ensure_license_for_current_tier()
            status = "✓"
        except license_guard.LicenseError:
            status = "✗"

        print(f"  {status} {feature_name:30} (tier={tier})")

# ============================================================================
# Example 7: Integration with CLI commands
# ============================================================================
print("\n[Example 7] Integration with CLI Commands")
print("-" * 70)

with DemoLicense(tier="pro"):
    from firsttry import cli

    # Show that tier is available in CLI context
    print(f"  CLI context tier: {license_guard.get_tier()}")
    print(f"  CLI context license key: {os.getenv('FIRSTTRY_LICENSE_KEY')}")
    print("  ✓ Ready for: firsttry run --tier pro")

# ============================================================================
# Summary
# ============================================================================
print("\n" + "=" * 70)
print("Demo License Summary")
print("=" * 70)

print(
    """
Demo License Key: demo-lic-key-2025

✓ Valid for all tiers: pro, promax, free-lite, free-strict
✓ Enabled by conftest.py automatically in pytest
✓ Safe for local development and CI/CD testing
✓ Uses ENV backend (no remote server needed)

Usage patterns:
  1. Direct environment setup (for scripts)
  2. DemoLicense class (for Python code)
  3. Context manager (for scoped testing)
  4. pytest fixtures (for test functions)
  5. conftest.py auto-setup (for all tests)

Environment Variables:
  FIRSTTRY_LICENSE_KEY=demo-lic-key-2025
  FIRSTTRY_LICENSE_BACKEND=env
  FIRSTTRY_LICENSE_ALLOW=pro,promax
  FIRSTTRY_TIER=pro (default, override per test)

For full documentation, see: DEMO_LICENSE_SETUP.md
"""
)

print("=" * 70)
print("Examples completed successfully! ✓")
print("=" * 70)
