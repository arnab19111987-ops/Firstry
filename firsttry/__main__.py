from __future__ import annotations

"""Module entrypoint for `python -m firsttry`.

This delegates to the click-based CLI defined in `firsttry.cli`.
"""

from .cli import main as cli_main


if __name__ == "__main__":
    # Invoke the Click entrypoint. Click will handle parsing and exit codes.
    cli_main()
