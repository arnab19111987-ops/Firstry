# tests/test_reports_tier_display.py
"""Tests for tier display formatting in reports."""
from firsttry.reports.tier_map import (
    get_tier_meta,
    is_tier_free,
    is_tier_paid,
    TIER_META,
)


def test_get_tier_meta_returns_dict():
    meta = get_tier_meta("free-lite")
    assert isinstance(meta, dict)
    assert "title" in meta
    assert "subtitle" in meta


def test_tier_meta_contains_human_readable_title():
    meta = get_tier_meta("pro")
    assert isinstance(meta["title"], str)
    assert "FirstTry" in meta["title"]
    assert "Pro" in meta["title"]


def test_tier_meta_contains_subtitle():
    meta = get_tier_meta("free-strict")
    assert isinstance(meta["subtitle"], str)
    assert len(meta["subtitle"]) > 0


def test_all_standard_tiers_have_metadata():
    """All standard tiers should have complete metadata."""
    standard_tiers = ["free-lite", "free-strict", "pro", "promax"]
    for tier in standard_tiers:
        meta = get_tier_meta(tier)
        assert "title" in meta
        assert "subtitle" in meta
        assert len(meta["title"]) > 0
        assert len(meta["subtitle"]) > 0


def test_tier_titles_distinct():
    """Each tier should have a distinct title."""
    tiers = ["free-lite", "free-strict", "pro", "promax"]
    titles = [get_tier_meta(t)["title"] for t in tiers]
    assert len(titles) == len(set(titles))


def test_is_tier_free_correctly_identifies_free_tiers():
    assert is_tier_free("free-lite") is True
    assert is_tier_free("free-strict") is True
    assert is_tier_free("pro") is False
    assert is_tier_free("promax") is False


def test_is_tier_paid_correctly_identifies_paid_tiers():
    assert is_tier_paid("pro") is True
    assert is_tier_paid("promax") is True
    assert is_tier_paid("free-lite") is False
    assert is_tier_paid("free-strict") is False


def test_tier_meta_constant_has_all_standard_tiers():
    """TIER_META should contain all standard tiers."""
    required_tiers = ["free-lite", "free-strict", "pro", "promax"]
    for tier in required_tiers:
        assert tier in TIER_META
