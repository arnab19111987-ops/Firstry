from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .intents import CommandIntent, get_intent


@dataclass
class ResolvedCommand:
    """
    What we actually run for a step.
    """
    intent_key: Optional[str]
    firsttry_intent: Optional[CommandIntent]
    used_cmd: str
    raw_cmd: str
    source: str
    fallback_possible: bool


def resolve_command_for_step(step: Dict[str, Any]) -> ResolvedCommand:
    """
    Apply the rule:
    - If an intent is present and a FirstTry command exists -> use FirstTry.
    - Else -> use raw CI command.
    """
    intent_key = step.get("intent")
    raw_cmd = (step.get("run") or "").strip()

    if not raw_cmd:
        raise ValueError(f"Step {step.get('id', '<unknown>')} is missing 'run' command")

    if not intent_key:
        return ResolvedCommand(
            intent_key=None,
            firsttry_intent=None,
            used_cmd=raw_cmd,
            raw_cmd=raw_cmd,
            source="raw",
            fallback_possible=False,
        )

    intent = get_intent(intent_key)
    if intent is None:
        return ResolvedCommand(
            intent_key=intent_key,
            firsttry_intent=None,
            used_cmd=raw_cmd,
            raw_cmd=raw_cmd,
            source="raw",
            fallback_possible=False,
        )

    if intent.firsttry_cmd:
        return ResolvedCommand(
            intent_key=intent_key,
            firsttry_intent=intent,
            used_cmd=intent.firsttry_cmd,
            raw_cmd=intent.raw_cmd or raw_cmd,
            source="firsttry",
            fallback_possible=True,
        )

    return ResolvedCommand(
        intent_key=intent_key,
        firsttry_intent=intent,
        used_cmd=intent.raw_cmd or raw_cmd,
        raw_cmd=intent.raw_cmd or raw_cmd,
        source="raw",
        fallback_possible=False,
    )
