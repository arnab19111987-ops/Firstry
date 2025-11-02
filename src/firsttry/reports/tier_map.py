# src/firsttry/reports/tier_map.py

TIER_CHECKS = {
    "free": ["ruff", "mypy", "pytest"],
    "pro": ["ruff", "mypy", "pytest", "bandit", "pip-audit", "ci-parity"],
    "team": ["ruff", "mypy", "pytest", "bandit", "pip-audit", "ci-parity", "coverage"],
    "enterprise": [
        "ruff",
        "mypy",
        "pytest",
        "bandit",
        "pip-audit",
        "ci-parity",
        "coverage",
        "secrets-scan",
    ],
}

LOCK_MESSAGE = "🔒 Locked — available in Pro/Team. Run `firsttry upgrade` to unlock."