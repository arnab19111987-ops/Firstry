"""
Example: Using legacy --gate and --require-license flags

This demonstrates that old FirstTry CLI invocations continue to work
even though these flags have been deprecated in favor of the new
mode-based CLI system.
"""

import subprocess
import sys


def run_with_legacy_gate_precommit():
    """
    Legacy: Run just ruff (pre-commit checks) with old --gate flag

    Modern equivalent:
        firsttry run fast
    """
    cmd = [sys.executable, "-m", "firsttry.cli", "run", "--gate", "pre-commit"]
    print(f"Running: {' '.join(cmd)}")
    # Will print deprecation notice, but continue to work
    subprocess.run(cmd)


def run_with_legacy_require_license():
    """
    Legacy: Run with license requirement (now: pro tier)

    Modern equivalent:
        firsttry run --tier pro
    """
    cmd = [sys.executable, "-m", "firsttry.cli", "run", "--require-license"]
    print(f"Running: {' '.join(cmd)}")
    # Will print deprecation notice, but continue to work
    subprocess.run(cmd)


def run_with_legacy_combined():
    """
    Legacy: Run strict checks with license requirement

    Modern equivalent:
        firsttry run strict --tier pro
    """
    cmd = [sys.executable, "-m", "firsttry.cli", "run", "--gate", "strict", "--require-license"]
    print(f"Running: {' '.join(cmd)}")
    # Will print deprecation notice, but continue to work
    subprocess.run(cmd)


def run_modern_equivalent():
    """Modern CLI usage (recommended)."""
    # Instead of: firsttry run --gate pre-commit
    # Use:
    cmd = [sys.executable, "-m", "firsttry.cli", "run", "fast"]
    print(f"Running (modern): {' '.join(cmd)}")
    subprocess.run(cmd)


if __name__ == "__main__":
    print("=" * 60)
    print("FirstTry Legacy Flag Backward Compatibility Demo")
    print("=" * 60)
    print()

    # Show the translation mapping
    print("DEPRECATION MAP:")
    print("-" * 60)
    print("Legacy                          → Modern")
    print("-" * 60)
    print("--gate pre-commit              → run fast")
    print("--gate ruff                    → run fast")
    print("--gate strict                  → run strict")
    print("--gate ci                      → run ci")
    print("--require-license              → run --tier pro")
    print("--gate strict --require-license → run strict --tier pro")
    print()

    print("KEY CHANGES:")
    print("-" * 60)
    print("1. Mode-based CLI: 'firsttry run <mode>'")
    print("   - fast:       ruff only (free)")
    print("   - strict/ci:  ruff + mypy + pytest (free)")
    print("   - pro:        full suite (requires license)")
    print("   - enterprise: enterprise features (requires license)")
    print()
    print("2. Tier control: --tier <tier>")
    print("   - free-lite, free-strict, pro, promax")
    print()
    print("3. No more per-gate flags: use modes instead")
    print()

    print("MIGRATION GUIDE:")
    print("-" * 60)
    print("Old command                    → New command")
    print("-" * 60)
    print("firsttry run --gate ruff       → firsttry run fast")
    print("firsttry run --gate strict     → firsttry run strict")
    print("firsttry run --require-license → firsttry run --tier pro")
    print("firsttry run --gate pre-commit → firsttry run fast")
    print("                                  --show-report")
    print()

    print("PRE-COMMIT HOOK EXAMPLES:")
    print("-" * 60)
    print()
    print("Old .pre-commit-config.yaml:")
    print(
        """
    - repo: local
      hooks:
        - id: firsttry
          name: FirstTry (old)
          entry: bash -c 'firsttry run --gate pre-commit'
          language: system
    """
    )
    print()
    print("New .pre-commit-config.yaml:")
    print(
        """
    - repo: local
      hooks:
        - id: firsttry
          name: FirstTry (new)
          entry: bash -lc 'PYTHONPATH=src python -m firsttry.cli run fast --show-report'
          language: system
    """
    )
    print()
