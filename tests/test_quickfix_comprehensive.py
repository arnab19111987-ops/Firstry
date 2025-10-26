from dataclasses import dataclass

from firsttry import quickfix as qf


@dataclass
class FakeCheck:
    name: str
    passed: bool
    output: str
    fix_hint: str = ""


def test_suggest_fix_ruff_not_found():
    hint = qf.suggest_fix("ruff check .", "", "ruff: command not found")
    assert hint is not None
    assert "pip install ruff" in hint


def test_suggest_fix_black_not_found():
    hint = qf.suggest_fix("black .", "", "black: command not found")
    assert hint is not None
    assert "pip install black" in hint


def test_suggest_fix_pytest_not_found():
    hint = qf.suggest_fix("pytest -q", "", "pytest: not found")
    assert hint is not None
    assert "pip install pytest" in hint


def test_suggest_fix_import_error():
    hint = qf.suggest_fix(
        "python test.py", "", "ModuleNotFoundError: No module named 'fastapi'"
    )
    assert hint is not None
    assert "fastapi" in hint
    assert "pip install" in hint


def test_suggest_fix_import_error_stdlib():
    # Should not suggest installing stdlib modules
    hint = qf.suggest_fix(
        "python test.py", "", "ModuleNotFoundError: No module named 'sys'"
    )
    assert hint is None


def test_suggest_fix_nameerror():
    hint = qf.suggest_fix("pytest", "", "NameError: name 'foo' is not defined")
    assert hint is not None
    assert "NameError" in hint


def test_suggest_fix_assertion_failure():
    hint = qf.suggest_fix("pytest", "AssertionError: assert 1 == 2", "")
    assert hint is not None
    assert "failing" in hint.lower()


def test_suggest_fix_unused_import():
    hint = qf.suggest_fix("ruff check .", "F401 unused import", "")
    assert hint is not None
    assert "ruff check . --fix" in hint


def test_suggest_fix_black_reformat():
    hint = qf.suggest_fix("black --check .", "would reformat 3 files", "")
    assert hint is not None
    assert "black ." in hint


def test_suggest_fix_no_match():
    hint = qf.suggest_fix("echo hello", "some random output", "")
    assert hint is None


def test_generate_quickfix_suggestions_database_url():
    checks = [FakeCheck("db", False, "KeyError: 'DATABASE_URL'")]
    suggestions = qf.generate_quickfix_suggestions(checks)
    assert len(suggestions) > 0
    assert any("DATABASE_URL" in s for s in suggestions)


def test_generate_quickfix_suggestions_import_error():
    checks = [FakeCheck("import", False, "ImportError: cannot import name 'Foo'")]
    suggestions = qf.generate_quickfix_suggestions(checks)
    assert len(suggestions) > 0
    assert any("Import error" in s for s in suggestions)


def test_generate_quickfix_suggestions_ruff_unused():
    checks = [FakeCheck("lint", False, "F401 'os' imported but unused")]
    suggestions = qf.generate_quickfix_suggestions(checks)
    assert len(suggestions) > 0
    assert any("ruff check . --fix" in s for s in suggestions)


def test_generate_quickfix_suggestions_black():
    checks = [FakeCheck("format", False, "would reformat file.py")]
    suggestions = qf.generate_quickfix_suggestions(checks)
    assert len(suggestions) > 0
    assert any("black ." in s for s in suggestions)


def test_generate_quickfix_suggestions_mypy():
    checks = [FakeCheck("types", False, "error: mypy found type issues")]
    suggestions = qf.generate_quickfix_suggestions(checks)
    assert len(suggestions) > 0
    assert any("type" in s.lower() for s in suggestions)


def test_generate_quickfix_suggestions_with_fix_hint():
    checks = [FakeCheck("custom", False, "some error", "Run: make fix")]
    suggestions = qf.generate_quickfix_suggestions(checks)
    assert "Run: make fix" in suggestions


def test_generate_quickfix_suggestions_deduplication():
    checks = [
        FakeCheck("a", False, "F401 unused import"),
        FakeCheck("b", False, "F401 unused import in another file"),
    ]
    suggestions = qf.generate_quickfix_suggestions(checks)
    # Should only have one ruff fix suggestion despite two checks matching
    ruff_suggestions = [s for s in suggestions if "ruff check . --fix" in s]
    assert len(ruff_suggestions) == 1
