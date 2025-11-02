# src/firsttry/license_guard.py
from __future__ import annotations

import os


def get_tier() -> str:
    """
    Return the current license tier with synonym support.
    
    Tier mappings:
    - free, developer → "developer" 
    - teams, pro → "teams"
    - enterprise, org → "enterprise"
    - default → "developer"
    """
    # Resolve from environment or cached license
    tier = os.getenv("FIRSTTRY_TIER", "").lower().strip()
    if tier in {"free", "developer"}:
        return "developer"
    elif tier in {"teams", "pro"}:
        return "teams"
    elif tier in {"enterprise", "org"}:
        return "enterprise"
    return "developer"


def is_pro() -> bool:
    return get_tier() == "teams"

def is_teams() -> bool:
    return get_tier() == "teams"

def is_developer() -> bool:
    return get_tier() == "developer"