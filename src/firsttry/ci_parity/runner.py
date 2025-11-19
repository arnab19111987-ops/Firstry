"""Runner entrypoint for CI parity tasks.

Provides a `run_gate` helper and a CLI `main` function so the module
can be invoked via `python -m firsttry.ci_parity.runner`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from .intents import (
    DEFAULT_MIRROR_PATH,
    DEFAULT_WORKFLOWS_ROOT,
    autofill_intents,
    lint_intents,
)


def run_ci(
    mirror_path: Optional[str | Path] = None,
    workflows_root: Optional[str | Path] = None,
) -> int:
    """
    Core CI parity check.

    For now, this delegates to lint_intents (structural parity check):
    - loads CI workflows,
    - loads ci_mirror.toml,
    - ensures all jobs are mapped.
    """
    return lint_intents(
        mirror_path=mirror_path or DEFAULT_MIRROR_PATH,
        workflows_root=workflows_root or DEFAULT_WORKFLOWS_ROOT,
    )


def run_gate(
    stage: str,
    mirror_path: Optional[str | Path] = None,
    workflows_root: Optional[str | Path] = None,
) -> int:
    """
    Gate implementation for `firsttry gate <stage>`.

    Stages:
      - dev:    lint intents only
      - merge:  lint + ci parity
      - release: same as merge (can be tightened later)

    Returns:
      0 on success,
      2 on gate failure (unmapped jobs etc),
      1 on internal error.
    """
    stage = stage.lower()
    mpath = mirror_path or DEFAULT_MIRROR_PATH
    wroot = workflows_root or DEFAULT_WORKFLOWS_ROOT

    if stage not in {"dev", "merge", "release"}:
        print(f"[ci-parity] ERROR: Unknown gate stage {stage!r}", file=sys.stderr)
        return 1

    # Step 1: lint intents for all stages
    lint_rc = lint_intents(mirror_path=mpath, workflows_root=wroot)
    if lint_rc not in (0, 2):
        # 1 = internal error
        print(
            f"[ci-parity] ERROR: lint_intents failed with exit code {lint_rc}",
            file=sys.stderr,
        )
        return 1

    if lint_rc == 2:
        # parity mismatch is a gate failure
        print(
            f"[ci-parity] Gate {stage}: FAILED (unmapped or stale intents)",
            file=sys.stderr,
        )
        return 2

    # For dev gate, we stop after lint.
    if stage == "dev":
        print("[ci-parity] Gate dev: OK")
        return 0

    # For merge/release, run CI parity check as well.
    ci_rc = run_ci(mirror_path=mpath, workflows_root=wroot)
    if ci_rc not in (0, 2):
        print(
            f"[ci-parity] ERROR: run_ci failed with exit code {ci_rc}", file=sys.stderr
        )
        return 1

    if ci_rc == 2:
        print(f"[ci-parity] Gate {stage}: FAILED (CI parity mismatch)", file=sys.stderr)
        return 2

    print(f"[ci-parity] Gate {stage}: OK")
    return 0


# === CLI entrypoint for `python -m firsttry.ci_parity.runner` ===


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m firsttry.ci_parity.runner",
        description="FirstTry CI parity utilities",
    )
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # `ci` subcommand
    ci_parser = subparsers.add_parser(
        "ci",
        help="Run CI parity check (currently structural intents linting).",
    )
    ci_parser.add_argument(
        "--mirror-path",
        default=str(DEFAULT_MIRROR_PATH),
        help="Path to ci_mirror.toml (default: .firsttry/ci_mirror.toml)",
    )
    ci_parser.add_argument(
        "--workflows-root",
        default=str(DEFAULT_WORKFLOWS_ROOT),
        help="Root directory for GitHub workflows (default: .github/workflows)",
    )

    # `gate` subcommand (optional direct usage)
    gate_parser = subparsers.add_parser(
        "gate",
        help="Run a CI parity gate (dev/merge/release).",
    )
    gate_parser.add_argument(
        "stage",
        choices=["dev", "merge", "release"],
        help="Gate stage to run.",
    )
    gate_parser.add_argument(
        "--mirror-path",
        default=str(DEFAULT_MIRROR_PATH),
        help="Path to ci_mirror.toml (default: .firsttry/ci_mirror.toml)",
    )
    gate_parser.add_argument(
        "--workflows-root",
        default=str(DEFAULT_WORKFLOWS_ROOT),
        help="Root directory for GitHub workflows (default: .github/workflows)",
    )

    # `autofill` subcommand (optional)
    autofill_parser = subparsers.add_parser(
        "autofill",
        help="Suggest or apply mirror entries for unmapped CI jobs.",
    )
    autofill_parser.add_argument(
        "--mirror-path",
        default=str(DEFAULT_MIRROR_PATH),
        help="Path to ci_mirror.toml (default: .firsttry/ci_mirror.toml)",
    )
    autofill_parser.add_argument(
        "--workflows-root",
        default=str(DEFAULT_WORKFLOWS_ROOT),
        help="Root directory for GitHub workflows (default: .github/workflows)",
    )
    autofill_parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print suggestions only; do not modify mirror.",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.cmd == "ci":
        return run_ci(
            mirror_path=args.mirror_path,
            workflows_root=args.workflows_root,
        )

    if args.cmd == "gate":
        return run_gate(
            stage=args.stage,
            mirror_path=args.mirror_path,
            workflows_root=args.workflows_root,
        )

    if args.cmd == "autofill":
        return autofill_intents(
            mirror_path=args.mirror_path,
            workflows_root=args.workflows_root,
            dry_run=args.dry_run,
        )

    parser.error(f"Unknown command {args.cmd!r}")
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
