from firsttry import quickfix


def test_quickfix_missing_ruff_tool():
    cmd = "ruff check ."
    stdout = ""
    stderr = "sh: ruff: command not found"
    hint = quickfix.suggest_fix(cmd, stdout, stderr)
    assert "pip install ruff" in hint


def test_quickfix_missing_black_tool():
    cmd = "black ."
    stdout = ""
    stderr = "black: not found"
    hint = quickfix.suggest_fix(cmd, stdout, stderr)
    assert "pip install black" in hint


def test_quickfix_importerror_module_not_found():
    cmd = "pytest -q"
    stdout = ""
    stderr = "ModuleNotFoundError: No module named 'cool_lib'"
    hint = quickfix.suggest_fix(cmd, stdout, stderr)
    # We expect it to extract the module name and suggest pip install <module>
    assert "cool_lib" in hint
    assert "pip install cool_lib" in hint


def test_quickfix_importerror_skips_stdlib():
    cmd = "pytest -q"
    stdout = ""
    stderr = "ImportError: No module named 'sys'"
    hint = quickfix.suggest_fix(cmd, stdout, stderr)
    # Should not offer to pip install stdlib
    assert hint is None


def test_quickfix_pytest_assertion():
    cmd = "pytest -q"
    stdout = "E   AssertionError: expected 200 got 500"
    stderr = ""
    hint = quickfix.suggest_fix(cmd, stdout, stderr)
    assert "Run pytest locally" in hint


def test_quickfix_nameerror():
    cmd = "pytest -q"
    stdout = ""
    stderr = "NameError: name 'create_app' is not defined"
    hint = quickfix.suggest_fix(cmd, stdout, stderr)
    assert "NameError" in hint or "undefined" in hint
    assert "Run pytest locally" in hint or "fix that symbol" in hint
