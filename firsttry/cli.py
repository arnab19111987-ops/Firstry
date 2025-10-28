from __future__ import annotations

import argparse
import subprocess
import shlex
import sys
from typing import Literal

from .scanner import run_all_checks_dry_run
from .report import (
    print_human_report,
    print_detailed_issue_table,
    print_after_autofix_report,
)


def _prompt_user_choice(
    has_autofixable: bool,
) -> Literal["details", "autofix", "cancel"]:
    """
    Ask the user what to do next.
    If nothing is autofixable, don't offer autofix.
    """
    if has_autofixable:
        print("What do you want to do next?\n")
        print("[1] Show detailed report with file-by-file issues")
        print("[2] Let FirstTry attempt safe fixes for autofixable issues")
        print("[3] Cancel (I'll fix manually)")
        answer = input("\nChoose 1 / 2 / 3: ").strip()
        if answer == "1":
            return "details"
        if answer == "2":
            return "autofix"
        return "cancel"
    else:
        print("No autofixable issues were found.")
        print("[1] Show detailed report with file-by-file issues")
        print("[2] Cancel")
        answer = input("\nChoose 1 / 2: ").strip()
        if answer == "1":
            return "details"
        return "cancel"


def _run_shell(cmd: str) -> tuple[int, str, str]:
    """
    Tiny helper for safe autofix.
    We run commands like 'black .' and 'ruff check --fix .'.
    We don't crash if tools aren't installed.
    """
    try:
        proc = subprocess.run(
            shlex.split(cmd) if isinstance(cmd, str) else cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        return 127, "", "not found"
    return proc.returncode, proc.stdout, proc.stderr


def _attempt_autofix_for_gate(scan) -> None:
    """
    Actually apply safe autofix for THIS gate.

    Gate strictness:
    - pre-commit: gentle (formatting, trivial lint)
    - pre-push / auto: may become stricter later; for now same base commands

    We use scan.autofix_cmds, which scanner.py built for this gate.
    """
    cmds = getattr(scan, "autofix_cmds", [])
    if not cmds:
        print("No autofix commands available for this gate (nothing to apply).")
        return

    print("Applying safe autofix steps:")
    for cmd in cmds:
        print(f"  $ {cmd}")
        rc, out, err = _run_shell(cmd)
        if rc == 127:
            print(f"    ↳ SKIP: tool not found for '{cmd}'")
        else:
            if rc == 0:
                print("    ↳ OK")
            else:
                print(f"    ↳ EXIT {rc} (continuing)")
    print()


def _install_git_hooks() -> int:
    """
    One-time convenience: drop FirstTry into .git/hooks so that:
      - pre-commit runs fast gate
      - pre-push runs full gate
    """
    import os
    import stat
    from pathlib import Path

    root = Path(".").resolve()
    git_dir = root / ".git"
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    pre_commit_body = """#!/bin/sh
# FirstTry pre-commit hook
exec python -m firsttry.cli run --gate pre-commit
"""
    pre_push_body = """#!/bin/sh
# FirstTry pre-push hook
exec python -m firsttry.cli run --gate pre-push
"""

    pre_commit_path = hooks_dir / "pre-commit"
    pre_push_path = hooks_dir / "pre-push"

    for path_obj, body in [
        (pre_commit_path, pre_commit_body),
        (pre_push_path, pre_push_body),
    ]:
        path_obj.write_text(body, encoding="utf-8")
        st = os.stat(path_obj)
        os.chmod(path_obj, st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print("✅ FirstTry git hooks installed:")
    print("   • pre-commit → fast gate (lint + types)")
    print("   • pre-push   → full gate (lint + types + security + tests + coverage)")
    print("From now on:")
    print("   git commit  will run FirstTry")
    print("   git push    will run FirstTry")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="firsttry",
        description="FirstTry: pass CI in one shot.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # firsttry run --gate pre-commit
    run_p = sub.add_parser(
        "run",
        help="Run a quality gate and print summary + autofix options.",
    )
    run_p.add_argument(
        "--gate",
        required=True,
        choices=["pre-commit", "pre-push", "auto"],
        help=(
            "Which gate to evaluate:\n"
            "  pre-commit  = fast checks (lint + types only)\n"
            "  pre-push    = full CI-grade (lint, types, security, tests, coverage)\n"
            "  auto        = adaptive full scan"
        ),
    )

    # firsttry install-hooks
    sub.add_parser(
        "install-hooks",
        help="Install git pre-commit / pre-push hooks that call FirstTry automatically.",
    )

    args = parser.parse_args(argv)

    # handle install-hooks first
    if args.cmd == "install-hooks":
        return _install_git_hooks()

    # handle run
    if args.cmd == "run":
        # 1. dry-run scan (no mutation)
        before_scan = run_all_checks_dry_run(gate_name=args.gate)

        # 2. high-level report with per-section counts
        print_human_report(before_scan)

        # 3. ask user what next
        choice = _prompt_user_choice(
            has_autofixable=(before_scan.total_autofixable > 0),
        )

        if choice == "details":
            print_detailed_issue_table(before_scan)
            return 0

        if choice == "cancel":
            print("No changes applied. Exiting.")
            return 0

        if choice == "autofix":
            # 4. apply safe autofix for THIS gate
            _attempt_autofix_for_gate(before_scan)

            # 5. rescan after autofix
            after_scan = run_all_checks_dry_run(gate_name=args.gate)

            # 6. show improvement
            print_after_autofix_report(before_scan, after_scan)
            return 0

    # should never get here if argparse is correct
    return 1


if __name__ == "__main__":
    sys.exit(main())
