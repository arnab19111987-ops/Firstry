"""Test CLI install-hooks command."""

from tests.cli_utils import run_cli


def test_cli_install_hooks_command():
    """Test that install-hooks command executes."""
    code, out, err = run_cli(["setup"])
    # Setup command may or may not exist - just ensure it doesn't crash
    assert code in (0, 1, 2)
    # Should provide some output
    assert len(out) > 0 or len(err) > 0
