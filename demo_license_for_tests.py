#!/usr/bin/env python3
"""
demo_license_for_tests.py

Demo pre-license setup for pytest testing.
Provides a universal demo license key valid for all tests.

Usage:
    # In conftest.py:
    from demo_license_for_tests import setup_demo_license, DemoLicense
    
    setup_demo_license()  # Enable demo license for all tests
    
    # Or manually in tests:
    @pytest.fixture
    def demo_license():
        return DemoLicense()
"""

import os
from pathlib import Path

# Universal demo license key - valid for all tiers and tests
DEMO_LICENSE_KEY = "demo-lic-key-2025"

# ENV backend for testing - always validates
DEMO_LICENSE_BACKEND = "env"


class DemoLicense:
    """Demo license manager for testing."""

    def __init__(self, tier: str = "pro"):
        """Initialize demo license with given tier.

        Args:
            tier: Tier to enable (pro, promax, free-lite, free-strict, etc.)
        """
        self.tier = self._normalize_tier(tier)
        self.original_env = {}

    @staticmethod
    def _normalize_tier(tier: str) -> str:
        """Normalize tier name to canonical form."""
        tier_lower = tier.lower().strip()

        if tier_lower in ("pro", "team", "teams", "full"):
            return "pro"
        elif tier_lower in ("promax", "enterprise", "org"):
            return "promax"
        elif tier_lower in ("free-lite", "free", "lite", "dev", "developer", "fast", "auto"):
            return "free-lite"
        elif tier_lower in ("free-strict", "strict", "ci", "config", "verify"):
            return "free-strict"
        else:
            return "pro"  # default

    def enable(self) -> None:
        """Enable demo license in environment."""
        # Save original values
        self.original_env = {
            "FIRSTTRY_LICENSE_KEY": os.getenv("FIRSTTRY_LICENSE_KEY"),
            "FIRSTTRY_TIER": os.getenv("FIRSTTRY_TIER"),
            "FIRSTTRY_LICENSE_BACKEND": os.getenv("FIRSTTRY_LICENSE_BACKEND"),
            "FIRSTTRY_LICENSE_ALLOW": os.getenv("FIRSTTRY_LICENSE_ALLOW"),
        }

        # Set demo license
        os.environ["FIRSTTRY_LICENSE_KEY"] = DEMO_LICENSE_KEY
        os.environ["FIRSTTRY_TIER"] = self.tier
        os.environ["FIRSTTRY_LICENSE_BACKEND"] = DEMO_LICENSE_BACKEND
        os.environ["FIRSTTRY_LICENSE_ALLOW"] = f"{self.tier},pro,promax"

    def disable(self) -> None:
        """Restore original environment."""
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def __enter__(self):
        """Context manager entry."""
        self.enable()
        return self

    def __exit__(self, *args):
        """Context manager exit."""
        self.disable()

    def __repr__(self) -> str:
        return f"DemoLicense(tier={self.tier!r}, key={DEMO_LICENSE_KEY!r})"


def setup_demo_license(tier: str = "pro") -> DemoLicense:
    """Setup demo license for testing session.

    Globally enables a demo license valid for all tests.
    This is safe to call multiple times.

    Args:
        tier: Tier to enable (pro, promax, free-lite, free-strict)

    Returns:
        DemoLicense instance (for reference)
    """
    license_mgr = DemoLicense(tier)
    license_mgr.enable()
    return license_mgr


# For conftest.py auto-loading
try:
    # Auto-enable demo license if this module is imported
    # (useful for pytest plugin auto-discovery)
    _demo_license = setup_demo_license()
    print(f"[demo-license] Auto-enabled demo license: {_demo_license}")
except Exception as e:
    # Fail silently if there's an issue (e.g., in non-pytest context)
    pass
