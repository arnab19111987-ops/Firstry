import firsttry.doctor as doc
import firsttry.quickfix as qf


def test_suggest_fix_tool_not_found_messages():
    assert "pip install ruff" in qf.suggest_fix("ruff check .", "", "command not found")
    assert "pip install black" in qf.suggest_fix("black --check .", "", "not found")
    assert "pip install pytest" in qf.suggest_fix("pytest -q", "", "not found")


def test_suggest_fix_import_error_pattern():
    out = "Traceback...\nModuleNotFoundError: No module named 'foobar'"
    hint = qf.suggest_fix("pytest -q", out, "")
    assert "pip install foobar" in hint


def test_suggest_fix_nameerror_and_assertion():
    hint1 = qf.suggest_fix("pytest -q", "NameError: x is not defined", "")
    assert "NameError" in hint1
    hint2 = qf.suggest_fix("pytest -q", "assert False", "")
    assert "Tests are failing" in hint2


def test_generate_quickfix_suggestions_accumulates_and_dedups():
    failing = [
        doc.CheckResult(name="mypy", passed=False, output="mypy: error: x"),
        doc.CheckResult(name="ruff", passed=False, output="unused import F401"),
        doc.CheckResult(name="black", passed=False, output="would reformat"),
        doc.CheckResult(name="pytest", passed=True, output="ok"),
        doc.CheckResult(name="custom", passed=False, output="", fix_hint="do thing"),
    ]
    tips = qf.generate_quickfix_suggestions(failing)
    joined = "\n".join(tips)
    assert "Mypy type errors" in joined
    assert "Ruff reports unused" in joined
    assert "Black formatting needed" in joined
    assert "do thing" in joined
