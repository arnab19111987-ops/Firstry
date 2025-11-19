"""Centralized constants for badge labels and tier rules."""

from __future__ import annotations

LEVELS = {
    1: {"code": "build_ready", "label": "Build Ready"},
    2: {"code": "ship_safe", "label": "Ship Safe"},
    3: {"code": "team_trusted", "label": "Team Trusted"},
    4: {"code": "production_perfect", "label": "Production Perfect"},
}

TIERS = {
    "developer": {"max_level": 2},
    "teams": {"max_level": 3},
    "enterprise": {"max_level": 4},
}
