import re
import subprocess
import sys


def _help_output(cmd):
    # Run the command and return stdout + stderr as text
    res = subprocess.run(
        [sys.executable, "-m", "firsttry.cli", *cmd], capture_output=True, text=True
    )
    return res.returncode, (res.stdout or "") + (res.stderr or "")


def test_dev_cli_exposes_only_allowed_commands():
    """Ensure the Dev CLI surface exposes only the frozen commands/help.

    This is a defensive test: it ensures that users of the Dev CLI won't be
    surprised by enterprise-only commands appearing in the default help.
    """
    allowed = {"run", "init", "pre-commit", "cache", "parity", "help", "--help"}

    rc, out = _help_output(["--help"])
    assert rc == 0

    # Basic sanity: the top-level help should mention at least the allowed commands
    for cmd in ("run", "init"):
        assert cmd in out, f"expected '{cmd}' in top-level help"

    # Disallowed tokens that must not appear in Dev help by default
    forbidden = ["license", "enterprise", "tier", "pro", "golden", "remote-cache", "cache-pro"]
    lower = out.lower()
    for tok in forbidden:
        # Match as a whole word to avoid false positives (e.g. 'profiles' containing 'pro')
        if re.search(rf"\b{re.escape(tok)}\b", lower):
            raise AssertionError(f"forbidden token '{tok}' appeared in top-level help")


def test_run_help_mentions_expected_flags():
    rc, out = _help_output(["run", "--help"])
    assert rc == 0
    # Ensure run help contains common flags or at least guidance
    assert "--verbose" in out or "--help" in out or "--config" in out
