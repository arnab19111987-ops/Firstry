# tests/test_quickfix.py
from firsttry.doctor import CheckResult
from firsttry.quickfix import generate_quickfix_suggestions


def test_quickfix_collects_suggestions_from_failed_checks_dedupes():
    failing_checks = [
        CheckResult(
            name="ruff",
            passed=False,
            output="F401 unused import foo",
            fix_hint="run ruff --fix",
        ),
        CheckResult(
            name="pytest",
            passed=False,
            output="E   ModuleNotFoundError: No module named 'capsule_core'",
            fix_hint="run tests locally",
        ),
        CheckResult(
            name="db",
            passed=False,
            output="KeyError: 'DATABASE_URL'",
            fix_hint=None,
        ),
    ]

    suggestions = generate_quickfix_suggestions(failing_checks)

    # Should have suggestions for ruff, import error, database, plus fix hints
    assert len(suggestions) >= 4

    # Check that we got the expected types of suggestions
    sug_text = " ".join(suggestions)
    assert "Ruff reports unused imports" in sug_text
    assert "Import error detected" in sug_text
    assert "DATABASE_URL" in sug_text
    assert "ruff --fix" in sug_text

    # We should not produce duplicates
    assert len(suggestions) == len(set(suggestions))
