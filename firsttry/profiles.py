from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class GateProfile:
    name: str
    gates: List[str]


# PHASE 1 profiles
_FAST = GateProfile(
    name="fast",
    gates=[
        "python:ruff",
        "python:mypy?",
        "python:pytest_fast?",
        "security:bandit?",
    ],
)

_STRICT = GateProfile(
    name="strict",
    gates=[
        # 1) environment health first
        "env:tools",
        "ci:files",

        # 2) core quality
        "python:ruff",
        "python:mypy",
        "python:pytest",

        # 3) parity / consistency
        "coverage:check",
        "deps:lock",
        "config:drift",

        # 4) optional / nice-to-have
        "precommit:all?",
        "python:black:check?",
        "drift:check?",
        "security:bandit?",
    ],
)

_RELEASE = GateProfile(
    name="release",
    gates=[
        "python:ruff",
        "python:black:check?",
        "python:mypy",
        "python:pytest",
        "coverage:xml",
        "security:bandit?",
        "drift:check?",
        "health:snapshot",
    ],
)


_PROFILES = {
    "fast": _FAST,
    "strict": _STRICT,
    "release": _RELEASE,
}


def list_profiles() -> list[str]:
    return list(_PROFILES.keys())


def get_profile(name: str) -> GateProfile:
    try:
        return _PROFILES[name]
    except KeyError as exc:
        raise KeyError(f"Unknown FirstTry profile: {name}") from exc
