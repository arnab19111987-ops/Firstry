"""Test license tier normalization and mappings."""

from firsttry.license_guard import get_tier


def test_get_tier_returns_valid_tier():
    """Test that get_tier returns a valid tier name."""
    tier = get_tier()
    assert tier is not None
    assert isinstance(tier, str)
    # Should be one of the known tiers
    known_tiers = [
        "free-lite",
        "free-strict",
        "pro",
        "promax",
        "developer",
        "basic",
        "teams",
        "enterprise",
    ]
    assert tier.lower() in [t.lower() for t in known_tiers]


def test_get_tier_is_deterministic():
    """Test that get_tier returns consistent results."""
    tier1 = get_tier()
    tier2 = get_tier()
    assert tier1 == tier2


def test_get_tier_returns_string():
    """Test that get_tier always returns a string."""
    tier = get_tier()
    assert isinstance(tier, str)
    assert len(tier) > 0
