import json

import firsttry.scanner as scanner
from firsttry.models import Issue


def test_run_cmd_missing_binary():
    # Use a binary name that almost certainly doesn't exist.
    code, out, err = scanner._run_cmd(["this-binary-should-not-exist-12345"])
    assert code == 127
    assert out == ""
    assert "not found" in err


def test_scan_with_ruff_parses_messages(monkeypatch):
    # Prepare a ruff-like JSON payload with a single message
    payload = [
        {
            "filename": "foo.py",
            "messages": [
                {
                    "code": "F401",
                    "message": "unused import 'json'",
                    "fix": None,
                    "location": {"row": 10, "column": 1},
                }
            ],
        }
    ]

    # Monkeypatch _run_cmd to return stdout with our JSON and exit code 0
    def fake_run(cmd):
        return 0, json.dumps(payload), ""

    monkeypatch.setattr(scanner, "_run_cmd", fake_run)

    issues = scanner._scan_with_ruff()
    assert isinstance(issues, list)
    assert len(issues) == 1
    issue = issues[0]
    assert isinstance(issue, Issue)
    assert issue.file == "foo.py"
    assert issue.line == 10
    # Since 'fix' was None, this should be classified as manual
    assert issue.autofixable is False


def test_scan_with_black_when_missing(monkeypatch):
    # Simulate black missing (return code 127)
    monkeypatch.setattr(scanner, "_run_cmd", lambda cmd: (127, "", ""))
    issues = scanner._scan_with_black()
    assert issues == []
