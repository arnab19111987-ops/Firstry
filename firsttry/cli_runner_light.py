"""
Temporary shim — forwards to cli_v2 so we don’t have 2 CLIs.
Remove this file once all callers use `python -m firsttry.cli_v2 ...`.
"""
from .cli_v2 import main


if __name__ == "__main__":
    raise SystemExit(main())
