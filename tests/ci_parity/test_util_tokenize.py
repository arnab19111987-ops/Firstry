from firsttry.ci_parity.util import normalize_cmd
from firsttry.ci_parity.util import tokenize_shell_line


def test_tokenize_quotes_and_no_backslash():
    line = 'pytest -q -k "not slow"'
    toks = tokenize_shell_line(line)
    # Should be exactly: pytest, -q, -k, not slow
    assert toks[:3] == ["pytest", "-q", "-k"]
    assert toks[3] == "not slow"
    # Normalize should not produce stray backslashes
    norm = normalize_cmd(toks)
    assert "\\" not in norm
