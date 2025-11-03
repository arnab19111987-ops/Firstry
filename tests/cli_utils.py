"""Test utilities for argparse-based CLI testing."""

from io import StringIO
import contextlib


def run_cli(args):
    """
    Run the firsttry CLI with given arguments and capture output.
    
    Args:
        args: List of command-line arguments (e.g., ["doctor", "--json"])
    
    Returns:
        Tuple of (exit_code, stdout, stderr)
    
    Example:
        code, out, err = run_cli(["doctor"])
        assert code == 0
        assert "Doctor" in out
    """
    from firsttry import cli
    
    out = StringIO()
    err = StringIO()
    
    # Redirect stdout and stderr to capture output
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            exit_code = cli.main(args)
            # If main doesn't explicitly return, treat as success
            if exit_code is None:
                exit_code = 0
        except SystemExit as e:
            # Handle sys.exit() calls
            exit_code = e.code if isinstance(e.code, int) else 1
        except Exception as e:
            # Unexpected exceptions should be treated as failures
            err.write(f"\nUnexpected exception: {e}\n")
            exit_code = 1
    
    return exit_code, out.getvalue(), err.getvalue()
