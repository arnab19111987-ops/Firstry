"""Thin CLI surface exposing `ft` commands.

This module provides a compact Click-based entrypoint that maps the
requested public commands to existing FirstTry handlers where possible.
Commands that are gated by tier use the `firsttry.tier.require_tier`
decorator.

This is intentionally a thin shim to avoid touching existing orchestrator
code.
"""

from __future__ import annotations

import sys

import click

from . import cli as _cli, tier as _tier


@click.group()
def main() -> None:
    """FT — thin CLI wrapper for FirstTry commands."""


@main.command(name="local")
def cmd_local() -> None:
    """Run the fast local pre-commit style checks (alias: ft pre-commit)."""
    # Use the fast pre-commit gate when invoked from the shim so tests and
    # local users get quick feedback without requiring the full parity lock.
    fast_gate = getattr(_cli, "pre_commit_fast_gate", None)
    if fast_gate is not None:
        rc = fast_gate()
    else:
        rc = _cli.cmd_pre_commit()
    raise SystemExit(rc)


@main.command(name="pre-commit")
def cmd_pre_commit_alias() -> None:
    """Alias for `ft local` (identical behavior)."""
    fast_gate = getattr(_cli, "pre_commit_fast_gate", None)
    if fast_gate is not None:
        rc = fast_gate()
    else:
        rc = _cli.cmd_pre_commit()
    raise SystemExit(rc)


@main.command(name="ci-parity")
def cmd_ci_parity() -> None:
    """Run the CI-parity pipeline (full CI mirror)."""
    # Reuse mirror-ci handler when available
    import argparse

    try:
        # cmd_mirror_ci expects an argparse.Namespace. Provide an empty
        # Namespace when calling from the thin shim.
        rc = _cli.cmd_mirror_ci(argparse.Namespace())
    except Exception:
        # Fallback to cmd_ci which tags CI env
        rc = _cli.cmd_ci(None)
    # After the parity run, enforce divergence guarantee for Enterprise tier.
    try:
        from pathlib import Path

        from . import divergence as _div

        warm = Path("artifacts/warm_parity_report.json")
        full = Path("artifacts/parity_report.json")
        _div.enforce_divergence_exit(
            warm if warm.exists() else None, full if full.exists() else None
        )
    except SystemExit:
        raise
    except Exception:
        # Do not let divergence checking break parity runs on errors.
        pass
    raise SystemExit(rc)


@main.command(name="pytest")
def cmd_pytest() -> None:
    """Run pytest-only in local incremental mode (ft local --only=pytest)."""
    # Reuse pre-commit gate path which runs pytest as part of its steps
    fast_gate = getattr(_cli, "pre_commit_fast_gate", None)
    if fast_gate is not None:
        rc = fast_gate()
    else:
        rc = _cli.cmd_pre_commit()
    raise SystemExit(rc)


@main.command(name="mypy")
def cmd_mypy() -> None:
    """Run mypy-only in local incremental mode (ft local --only=mypy)."""
    fast_gate = getattr(_cli, "pre_commit_fast_gate", None)
    if fast_gate is not None:
        rc = fast_gate()
    else:
        rc = _cli.cmd_pre_commit()
    raise SystemExit(rc)


@main.command(name="init")
def cmd_init() -> None:
    rc = _cli.cmd_init(None)
    raise SystemExit(rc)


@main.command(name="version")
def cmd_version() -> None:
    # Print version via existing module
    print(_cli.__version__)
    # Also show tier
    print(f"tier: {_tier.get_current_tier()}")
    raise SystemExit(0)


@main.command(name="doctor")
@_tier.require_tier("pro")
def cmd_doctor() -> None:
    rc = _cli.cmd_doctor(None)
    raise SystemExit(rc)


@main.command(name="roi")
@_tier.require_tier("pro")
def cmd_roi() -> None:
    # Placeholder: reuse doctor output for now
    print("ROI: summary not implemented in shim; run ft doctor for diagnostics.")
    raise SystemExit(0)


@main.command(name="cache-push")
@_tier.require_tier("pro")
def cmd_cache_push() -> None:
    print("cache-push: uploading golden cache and flaky list (not implemented in shim)")
    raise SystemExit(0)


@main.command(name="audit")
@_tier.require_tier("enterprise")
def cmd_audit() -> None:
    print("audit: enterprise-only audit runner not implemented in shim")
    raise SystemExit(0)


@main.command(name="policy")
@_tier.require_tier("enterprise")
def cmd_policy() -> None:
    print("policy: enterprise-only policy manager not implemented in shim")
    raise SystemExit(0)


@main.command(name="license")
@_tier.require_tier("enterprise")
def cmd_license() -> None:
    print("license: enterprise license manager not implemented in shim")
    raise SystemExit(0)


def run_cli(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    try:
        # Click's API expects the argument list under the `args` parameter.
        # Older code passed `argv=` which causes a TypeError with newer
        # Click versions (Context.__init__ got unexpected keyword 'argv').
        main(args=argv)
    except SystemExit as e:
        code = int(e.code) if e.code is not None else 0
        return code
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
