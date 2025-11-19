import pytest
from src.firsttry.cli_aliases import FT_ALIAS_MAP
from src.firsttry import pipelines

def test_ft_pytest_uses_valid_tier():
    spec = FT_ALIAS_MAP["pytest"]
    assert "--tier" in spec.args
    tier_index = list(spec.args).index("--tier")
    tier_name = spec.args[tier_index + 1]
    # Collect valid tiers from python pipeline
    valid_tiers = set()
    for step in pipelines.PYTHON_PIPELINE:
        t = step.get("tier")
        if isinstance(t, str):
            valid_tiers.add(t)
        elif isinstance(t, int):
            valid_tiers.add(str(t))
    # Accept some known aliases for test
    valid_tiers.update(["strict", "free-strict", "fast", "free-lite"])
    assert tier_name in valid_tiers, f"ft pytest uses invalid tier {tier_name!r}, valid tiers: {sorted(valid_tiers)}"
