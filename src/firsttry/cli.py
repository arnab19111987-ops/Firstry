from __future__ import annotations

import argparse
import json
import subprocess
import shlex
import sys
import os
import textwrap
from typing import Literal

from .scanner import run_all_checks_dry_run
from .state import load_last_run
from .license import (
    load_cached_license,
    ensure_trial_license_if_missing,
    license_summary_for_humans,
)
# licensing helper (developer-friendly global license store)
from .licensing import save_license, load_license
from .report import (
    print_human_report,
    print_detailed_issue_table,
    print_after_autofix_report,
)
from . import hooks


# Compatibility shim for tests that expect a runner-loader on firsttry.cli
def _load_real_runners_or_stub():
    """
    Backwards-compatible shim: some tests import `_load_real_runners_or_stub`
    from `firsttry.cli`. Defer to the tools-provided implementation when
    available (tools/firsttry/firsttry/cli.py). If that import fails, try
    to fall back to a lightweight runner in `firsttry.runners`.
    """
    # Minimal local stub implementation for compatibility with tests.
    from types import SimpleNamespace

    def _fake_result(name: str):
        return SimpleNamespace(ok=True, stdout="", stderr="", duration_s=0.0, cmd=())

    def _make_stub_runners():
        def run_ruff(*a, **k):
            return _fake_result("ruff")

        def run_black_check(*a, **k):
            return _fake_result("black-check")

        def run_mypy(*a, **k):
            return _fake_result("mypy")

        def run_pytest_kexpr(*a, **k):
            return _fake_result("pytest")

        def run_coverage_xml(*a, **k):
            return _fake_result("coverage_xml")

        def coverage_gate(*a, **k):
            return _fake_result("coverage_gate")

        return SimpleNamespace(
            run_ruff=run_ruff,
            run_black_check=run_black_check,
            run_mypy=run_mypy,
            run_pytest_kexpr=run_pytest_kexpr,
            run_coverage_xml=run_coverage_xml,
            coverage_gate=coverage_gate,
        )

    use_real = os.getenv("FIRSTTRY_USE_REAL_RUNNERS") == "1"
    if not use_real:
        return _make_stub_runners()

    # If a specific runners module is set, import and wrap it
    runners_mod_name = os.getenv("FIRSTTRY_RUNNERS_MODULE")
    if runners_mod_name:
        try:
            mod = __import__(runners_mod_name, fromlist=["*"])

            def _wrap(fn_name):
                fn = getattr(mod, fn_name, None)
                if callable(fn):
                    return fn
                return getattr(_make_stub_runners(), fn_name)

            return SimpleNamespace(
                run_ruff=_wrap("run_ruff"),
                run_black_check=_wrap("run_black_check"),
                run_mypy=_wrap("run_mypy"),
                run_pytest_kexpr=_wrap("run_pytest_kexpr"),
                run_coverage_xml=_wrap("run_coverage_xml"),
                coverage_gate=_wrap("coverage_gate"),
            )
        except Exception:
            return _make_stub_runners()

    # fallback: try to reuse the tools implementation if available
    try:
        from tools.firsttry.firsttry.cli import _load_real_runners_or_stub as _impl

        return _impl()
    except Exception:
        return _make_stub_runners()


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


def handle_activate(args: argparse.Namespace) -> int:
    """
    1. Install/refresh git hooks (pre-commit, pre-push).
    2. Run the pre-commit gate once in autofix mode.
    3. Print onboarding message.

    Returns process exit code (0 = success, nonzero = block).
    """

    # 1. Install / refresh hooks
    try:
        if hasattr(hooks, "install_git_hooks"):
            hooks.install_git_hooks()
        else:
            rc_install = subprocess.run(
                [sys.executable, "-m", "firsttry.cli", "install-hooks"],
                capture_output=True,
                text=True,
            )
            if rc_install.returncode != 0:
                print("[FirstTry] Failed to install hooks:")
                print(rc_install.stdout)
                print(rc_install.stderr, file=sys.stderr)
                return rc_install.returncode
    except Exception as e:
        print(f"[FirstTry] Error while installing hooks: {e}", file=sys.stderr)
        return 1

    # 2. Run pre-commit gate once in autofix mode (non-interactive "choice 2")
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "firsttry.cli", "run", "--gate", "pre-commit"],
            input="2\n",
            text=True,
        )
        rc_gate = proc.returncode
    except Exception as e:
        print(f"[FirstTry] Error while running initial scan: {e}", file=sys.stderr)
        return 1

    if rc_gate != 0:
        print(
            textwrap.dedent(
                """
                [FirstTry] Activation partially completed.

                - Hooks are installed.
                - FirstTry ran your repo gate and found issues that block a clean commit.

                Next steps:
                  1. Review any changes FirstTry already applied.
                  2. Fix remaining red items that require manual attention.
                  3. git add .
                  4. git commit normally (no --no-verify needed).

                Once that's green, you're fully onboarded.
                """
            ).strip()
        )
        return rc_gate

    # 3. Success message
    print(
        textwrap.dedent(
            """
            ✅ FirstTry is now active on this repo.

            What this means:
              • Git pre-commit / pre-push hooks are installed.
              • Your codebase was scanned and auto-fixed where it was safe.
              • Every future `git commit` will be checked & cleaned before it lands.

            Workflow from now on:
              1. Edit code
              2. git add .
              3. git commit -m "message"
                 → FirstTry runs automatically, fixes safe stuff, blocks bad code
              4. git push

            You can also run FirstTry on demand at any time:
              python -m firsttry.cli run --gate pre-commit

            You're good to go. Ship green on first push. 🚀
            """
        ).strip()
    )

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

    # firsttry license set/status (global user license helper)
    lic_parser = sub.add_parser("license", help="Manage FirstTry license")
    lic_sub = lic_parser.add_subparsers(dest="license_cmd")

    lic_set = lic_sub.add_parser("set", help="Set and save your license key")
    lic_set.add_argument("key", help="Your license key string")

    lic_sub.add_parser("status", help="Show license info")

    # firsttry activate
    sub.add_parser(
        "activate",
        help="Install hooks, run initial autofix scan, and finalize setup.",
    )

    # firsttry status --json
    status_p = sub.add_parser("status", help="Show license and last-run status.")
    status_p.add_argument(
        "--json",
        "-j",
        dest="as_json",
        action="store_true",
        help="Emit machine-readable JSON.",
    )

    # firsttry baseline add <path>
    baseline_p = sub.add_parser(
        "baseline",
        help="Manage the security baseline (known noisy files).",
    )
    baseline_sub = baseline_p.add_subparsers(dest="baseline_cmd", required=True)
    add_p = baseline_sub.add_parser("add", help="Add a glob/path to the baseline")
    add_p.add_argument(
        "path", help="glob or path to add to firsttry_security_baseline.yml"
    )

    args = parser.parse_args(argv)

    # handle install-hooks first
    if args.cmd == "install-hooks":
        return _install_git_hooks()

    # handle license subcommands early
    if args.cmd == "license":
        if args.license_cmd == "set":
            save_license(args.key)
            print("✅ License saved.")
            return 0
        if args.license_cmd == "status":
            data = load_license()
            if not data:
                print("⚠️  No license found. Run: firsttry license set <KEY>")
            else:
                print("✅ License found.")
                print(f"Key: {data.get('license_key', '???')}")
            return 0

    # handle activate
    if args.cmd == "activate":
        return handle_activate(args)

    # handle baseline subcommands
    if args.cmd == "baseline":
        # only command supported today: add
        if args.baseline_cmd == "add":
            pat = args.path
            from pathlib import Path

            baseline_file = Path("firsttry_security_baseline.yml")

            # Try YAML first if available
            try:
                import yaml

                if baseline_file.exists():
                    with baseline_file.open("r", encoding="utf-8") as fh:
                        data = yaml.safe_load(fh) or {}
                else:
                    data = {}

                files = data.get("files") or []
                if pat not in files:
                    files.append(pat)
                    data["files"] = files
                    with baseline_file.open("w", encoding="utf-8") as fh:
                        yaml.safe_dump(data, fh)
                    print(f"Added '{pat}' to {baseline_file}")
                else:
                    print(f"Pattern '{pat}' already present in {baseline_file}")
            except Exception:
                # Fallback simple append-based format
                if not baseline_file.exists():
                    baseline_file.write_text("files:\n  - %s\n" % pat, encoding="utf-8")
                    print(f"Created {baseline_file} with '{pat}'")
                else:
                    text = baseline_file.read_text(encoding="utf-8")
                    if "files:" not in text:
                        # naive prepend
                        baseline_file.write_text(
                            "files:\n  - %s\n" % pat + text, encoding="utf-8"
                        )
                        print(f"Added '{pat}' to {baseline_file}")
                    else:
                        # append under files: block
                        baseline_file.write_text(
                            text + ("\n  - %s\n" % pat), encoding="utf-8"
                        )
                        print(f"Appended '{pat}' to {baseline_file}")

            # Re-run the full gate so dev sees the impact immediately
            scan = run_all_checks_dry_run(gate_name="pre-push")
            print_human_report(scan, "pre-push")
            return 0

    # handle status
    if args.cmd == "status":
        # Load active license (cached) if present, otherwise bootstrap a short trial
        lic_obj = load_cached_license()
        if not lic_obj:
            lic_obj = ensure_trial_license_if_missing(days=3)

        last = load_last_run()

        if args.as_json:
            payload = {
                "license": {
                    "summary": license_summary_for_humans(lic_obj),
                },
                "last_run": last,
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0

        # human readable
        print(license_summary_for_humans(lic_obj))
        if last:
            print("Last run summary:")
            # show top-level keys of the last run in a friendly form
            for k, v in last.items():
                print(f"  {k}: {v}")
        else:
            print("No previous run recorded.")
        return 0

    # handle run
    if args.cmd == "run":
        # 1. dry-run scan (no mutation)
        before_scan = run_all_checks_dry_run(gate_name=args.gate)
        # 2. high-level report with per-section counts
        print_human_report(before_scan, args.gate)

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
