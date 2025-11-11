"""Install Git hooks for CI Parity enforcement.

This module installs pre-commit and pre-push hooks that run parity checks:
- pre-commit: Fast self-check (versions/config/plugins)
- pre-push: Full parity run (all gates + coverage)

Usage:
    python -m firsttry.ci_parity.install_hooks
"""

import os
import stat
import sys
from pathlib import Path

PRE_COMMIT = """#!/usr/bin/env bash
set -eo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
if [ ! -f "$REPO_ROOT/ci/parity.lock.json" ]; then exit 0; fi
if [ -x "$REPO_ROOT/.venv-parity/bin/python" ]; then
  . "$REPO_ROOT/.venv-parity/bin/activate"
fi
python -c "from firsttry.ci_parity.parity_runner import main; import sys; sys.exit(main(['--self-check','--explain']))"
"""

PRE_PUSH = """#!/usr/bin/env bash
set -eo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
if [ ! -f "$REPO_ROOT/ci/parity.lock.json" ]; then exit 0; fi
if [ -x "$REPO_ROOT/.venv-parity/bin/python" ]; then
  . "$REPO_ROOT/.venv-parity/bin/activate"
fi
export FT_NO_NETWORK=1
python -c "from firsttry.ci_parity.parity_runner import main; import sys; sys.exit(main(['--parity','--explain']))"
"""


def _write_hook(path: Path, content: str) -> None:
    """Write hook script and make it executable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def main() -> None:
    """Install parity pre-commit and pre-push hooks."""
    # Respect custom hooksPath if set
    hooks_path = os.popen("git config --get core.hooksPath 2>/dev/null").read().strip()
    if not hooks_path:
        hooks_dir = Path(".git/hooks")
    else:
        hooks_dir = Path(hooks_path)
    
    if not hooks_dir.parent.exists():
        print("[firsttry] Not in a Git repository, skipping hook installation", file=sys.stderr)
        return
    
    _write_hook(hooks_dir / "pre-commit", PRE_COMMIT)
    _write_hook(hooks_dir / "pre-push", PRE_PUSH)
    print(f"[firsttry] Installed parity pre-commit and pre-push hooks to {hooks_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
