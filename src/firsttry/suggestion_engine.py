# src/firsttry/suggestion_engine.py
from __future__ import annotations

from typing import Any, Dict, Optional

RUFF_HINTS = {
    "F401": "Remove the unused import, or use it, or add it to __all__.",
    "F841": "You assigned to a variable but never used it — remove it or use it.",
    "E501": "Line too long — wrap or add `# noqa: E501` if intentional.",
}

MYPY_HINTS = {
    "arg-type": "Argument type mismatch — change the function signature or cast the value before passing.",
    "attr-defined": "Attribute not defined — initialize it in __init__ or refine the type.",
}

PYTEST_HINTS = {
    "ImportError": "Tests cannot import your package — check PYTHONPATH or install with `pip install -e .`.",
    "FixtureLookupError": "Fixture not found — check the fixture name or ensure conftest.py is in the right folder.",
}

ESLINT_HINTS = {
    "no-unused-vars": "Remove the unused variable or prefix with `_` to mark it intentional.",
    "no-undef": "Variable not defined — import it or declare it.",
}

GENERIC_HINTS = {
    "permission": "Check file permissions or run the tool once manually to create its cache.",
    "timeout": "Tool took too long — reduce the scope or run it directly to debug.",
}


def suggest(tool: str, code: Optional[str], message: str) -> Optional[str]:
    tool = (tool or "").lower()

    if tool == "ruff" and code and code in RUFF_HINTS:
        return RUFF_HINTS[code]

    if tool == "mypy" and code:
        if code in MYPY_HINTS:
            return MYPY_HINTS[code]

    if tool == "eslint" and code:
        if code in ESLINT_HINTS:
            return ESLINT_HINTS[code]

    if tool == "pytest":
        for key, hint in PYTEST_HINTS.items():
            if key in message:
                return hint

    for key, hint in GENERIC_HINTS.items():
        if key in message.lower():
            return hint

    return None


def decorate_result(
    result: Dict[str, Any], tool: str, code: Optional[str], message: str
) -> Dict[str, Any]:
    hint = suggest(tool, code, message)
    if hint:
        result["hint"] = hint
    return result
