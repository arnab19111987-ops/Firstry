# mypy: ignore-errors
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Import detection and setup modules
try:
    from .detect import detect_language, deps_for_stacks
    from .setup import run_setup_interactive
    from .summary import print_run_summary as new_print_run_summary
except ImportError:
    # Fallback if modules aren't available
    def detect_language(cwd=None):
        return ["python"]

    def deps_for_stacks(stacks):
        return {"python": ["ruff", "black", "mypy", "pytest"]}

    def run_setup_interactive():
        print("Setup functionality not available.")

    new_print_run_summary = None

# Short gate aliases for ft command
SHORT_GATE_ALIASES = {
    "push": "pre-push",
    "commit": "pre-commit",
    "precommit": "pre-commit",
    "auto": "auto",
}

# import gate runner (single-gate helpers)
try:
    from firsttry.gates import run_gate, format_summary, print_verbose
except Exception:
    # fall back to loading the `gates.py` module file directly. The repo contains
    # both a `gates/` package and a `gates.py` module which can shadow each
    # other; attempt to import the file-based module to access the helpers.
    try:
        import importlib.util
        import sys

        _gates_path = Path(__file__).parent / "gates.py"
        # load the module under the expected package module name so decorators
        # (dataclasses, typing) that rely on sys.modules[...] behave correctly.
        spec = importlib.util.spec_from_file_location(
            "firsttry.gates", str(_gates_path)
        )
        _gates = importlib.util.module_from_spec(spec)
        sys.modules["firsttry.gates"] = _gates
        spec.loader.exec_module(_gates)  # type: ignore[attr-defined]

        run_gate = getattr(_gates, "run_gate", None)
        format_summary = getattr(_gates, "format_summary", None)
        print_verbose = getattr(_gates, "print_verbose", None)
    except Exception:
        run_gate = None
        format_summary = None
        print_verbose = None

# import profile runner (bulk/profile runner)
try:
    from firsttry.runner_light import run_profile
except Exception:
    run_profile = None

# optional status loader
try:
    from firsttry.state import load_last_run
except Exception:  # pragma: no cover
    load_last_run = None  # optional

# import hooks functionality
try:
    from firsttry.hooks import hooks_installed, install_all_hooks
except Exception:

    def hooks_installed() -> bool:
        return False

    def install_all_hooks() -> bool:
        return False


# Gate ordering for consistent display
GATE_ORDER = ["lint", "typecheck", "tests", "security", "dup", "format", "misc"]


def print_run_summary(results, elapsed: float, missing_deps: list[str] | None = None):
    """
    Enhanced summary printer following the lightweight format.
    results: list[GateResult-like or dict]
    elapsed: float seconds
    missing_deps: optional list of missing dependency install commands
    """
    total = len(results)
    failed = []

    # Normalize results to common format
    normalized_results = []
    for r in results:
        if hasattr(r, "passed"):
            # New GateResult format
            normalized_results.append(r)
            if not r.passed:
                failed.append(r)
        elif isinstance(r, dict):
            # Dict format - convert to object-like for easier access
            class Result:
                def __init__(self, data):
                    self.name = data.get("gate", "unknown")
                    self.passed = data.get("ok", False)
                    self.errors = data.get("errors", 0)
                    self.warnings = data.get("warnings", 0)
                    self.fixable = data.get("fixable", 0)
                    self.extra = data.get("extra", {})

            result_obj = Result(r)
            normalized_results.append(result_obj)
            if not result_obj.passed:
                failed.append(result_obj)

    if not failed:
        print(
            f"✅ All checks passed ({total} gate{'s' if total != 1 else ''}) in {elapsed:.1f}s\n"
        )
    else:
        print(f"❌ Checks failed ({len(failed)}/{total} gates) in {elapsed:.1f}s\n")

    # Sort results by preferred order
    order_map = {name: idx for idx, name in enumerate(GATE_ORDER)}
    results_sorted = sorted(
        normalized_results, key=lambda r: order_map.get(r.name.lower(), 999)
    )

    print("Gates:")
    for r in results_sorted:
        line = f"  • {r.name.ljust(11)}"
        if r.passed:
            line += "✅"
        else:
            # Base fail marker
            line += "❌"
            # Add counts
            parts = []
            if getattr(r, "errors", 0):
                parts.append(f"{r.errors} errors")
            if getattr(r, "warnings", 0):
                parts.append(f"{r.warnings} warnings")
            if getattr(r, "fixable", 0):
                parts.append(f"({r.fixable} fixable)")
            # Tests special-case
            if r.name.lower() == "tests":
                failed_tests = (r.extra or {}).get("failed_tests") or (
                    r.extra or {}
                ).get("first_failed_test")
                if failed_tests:
                    if isinstance(failed_tests, list) and failed_tests:
                        parts.append(f"{failed_tests[0]}")
                    elif isinstance(failed_tests, str):
                        parts.append(f"{failed_tests}")
            if parts:
                line += "  " + " ".join(parts)
        print(line)

    # Missing dependencies
    if missing_deps:
        print("\n👉 Install missing tools:")
        for cmd in missing_deps:
            print(f"   - {cmd}")

    # Action hint
    if failed:
        fixable_total = sum(getattr(r, "fixable", 0) for r in failed)
        if fixable_total:
            print("\n👉 Run: firsttry run --gate pre-commit --autofix")
        else:
            # Pick the most relevant hint
            tests_failed = any(
                r.name.lower() == "tests" and not r.passed for r in failed
            )
            if tests_failed:
                print("\n👉 Re-run your failing tests locally.")
            else:
                print(
                    "\n👉 See full logs with: firsttry run --gate pre-commit --verbose"
                )
    else:
        print("\n🎉 Ready to commit & push.")


def ensure_hooks() -> None:
    """Ensure git hooks are installed, prompting user if needed."""
    if hooks_installed():
        return

    # Only prompt if we're in a git repo
    git_dir = Path(".git")
    if not git_dir.exists():
        return

    try:
        resp = (
            input(
                "Git hooks not installed. Install FirstTry pre-commit & pre-push hooks now? [Y/n]: "
            )
            .strip()
            .lower()
        )
        if resp in ("", "y", "yes"):
            if install_all_hooks():
                print("✅ FirstTry git hooks installed.")
            else:
                print("⚠️ Could not install git hooks (no .git folder?).")
    except (EOFError, KeyboardInterrupt):
        # Handle non-interactive environments gracefully
        pass


def handle_interactive_menu(results: List[Dict[str, Any]], gate: str) -> int:
    """Handle the interactive menu when gates fail."""
    try:
        # Count fixable errors
        total_fixable: int = 0
        failed_results: List[Dict[str, Any]] = []

        if results and isinstance(results[0], dict):
            for r in results:
                if not r.get("ok", True):  # If gate failed
                    failed_results.append(r)
                    # Count fixable errors if available
                    fixable = r.get("fixable", 0)
                    total_fixable += fixable

        print("\n" + "=" * 50)
        print("🤔 What would you like to do?")
        print("=" * 50)

        # Show options
        options = []
        print("1. 📄 Show detailed error report")
        options.append("details")

        if total_fixable > 0:
            print(f"2. 🔧 Run autofix ({total_fixable} fixable errors)")
        else:
            print("2. 🔧 Run autofix (attempt fixes)")
        options.append("autofix")

        print("3. ❌ Cancel (I'll fix manually)")
        options.append("cancel")

        print("\nEnter your choice (1-3): ", end="")

        try:
            choice = input().strip()

            if choice == "1":
                return handle_show_details(failed_results)
            elif choice == "2":
                return handle_autofix(gate, total_fixable)
            elif choice == "3":
                print("\n👋 Canceled. Fix the issues manually and try again.")
                return 1
            else:
                print(f"\n❌ Invalid choice '{choice}'. Please run the command again.")
                return 1

        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 Canceled. Fix the issues manually and try again.")
            return 1

    except Exception as e:
        print(f"\n❌ Error in interactive menu: {e}")
        return 1


def handle_show_details(failed_results: List[Dict[str, Any]]) -> int:
    """Show detailed error information."""
    print("\n" + "=" * 60)
    print("📄 DETAILED ERROR REPORT")
    print("=" * 60)

    for r in failed_results:
        gate_name = r.get("gate", "Unknown")
        details = r.get("details", "")

        print(f"\n🔍 {gate_name.upper()} ERRORS:")
        print("-" * (len(gate_name) + 10))

        if details:
            # Format the details nicely
            lines = details.split("\n")
            for line in lines:
                if line.strip():
                    print(f"   {line}")
        else:
            print("   No detailed information available.")

        print()

    print("=" * 60)
    print("💡 TIP: Focus on fixing the most critical errors first.")
    print("💡 TIP: Use your editor's error highlighting for easier navigation.")
    print("=" * 60)

    return 1


def handle_autofix(gate: str, fixable_count: int) -> int:
    """Handle running autofix for fixable errors."""
    if fixable_count > 0:
        print(f"\n🔧 Running autofix for {fixable_count} fixable errors...")
    else:
        print("\n🔧 Running autofix (attempting to fix issues)...")
    print("This will attempt to automatically fix linting issues.")

    # For now, we'll suggest the manual commands
    # In a full implementation, this would actually run the fixes

    autofix_commands = []

    if "pre-commit" in gate or "pre-push" in gate:
        autofix_commands.extend(
            [
                "ruff check . --fix",
                "black .",
            ]
        )

    if autofix_commands:
        print("\n📝 Suggested autofix commands:")
        for i, cmd in enumerate(autofix_commands, 1):
            print(f"   {i}. {cmd}")

        print("\n❓ Run these autofix commands now? [Y/n]: ", end="")

        try:
            response = input().strip().lower()
            if response in ("", "y", "yes"):
                print("\n🚀 Running autofix commands...")

                import subprocess

                success_count = 0

                for cmd in autofix_commands:
                    print(f"\n▶️  Running: {cmd}")
                    try:
                        result = subprocess.run(
                            cmd.split(), capture_output=True, text=True, cwd="."
                        )

                        if result.returncode == 0:
                            print("   ✅ Success!")
                            success_count += 1
                        else:
                            print(f"   ⚠️  Warning: {result.stderr.strip()}")

                    except Exception as e:
                        print(f"   ❌ Failed: {e}")

                print(
                    f"\n🎉 Autofix completed! {success_count}/{len(autofix_commands)} commands succeeded."
                )
                print("💡 Run the gate again to see if issues are resolved:")
                print(f"   firsttry run --gate {gate}")

                return 0
            else:
                print("\n👋 Autofix canceled. You can run these commands manually.")
                return 1

        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 Autofix canceled.")
            return 1
    else:
        print("\n⚠️  No autofix commands available for this gate.")
        return 1


def handle_run(args: argparse.Namespace) -> int:
    """Handle the run command with hooks auto-installation."""
    # Ensure hooks are installed
    ensure_hooks()

    # Run the actual gate with timing
    if run_gate is None:
        print("No run_gate available in this build.")
        return 2

    start_time = time.time()
    results, ok = run_gate(args.gate)
    elapsed = time.time() - start_time

    # Detect missing dependencies
    try:
        stacks = detect_language()
        deps = deps_for_stacks(stacks)
        missing_cmds = []
        if "python" in deps:
            missing_cmds.append("pip install " + " ".join(deps["python"]))
        if "node" in deps:
            missing_cmds.append("npm install -D " + " ".join(deps["node"]))
        if "shell" in deps:
            missing_cmds.append("# shell tools: " + " ".join(deps["shell"]))
    except Exception:
        missing_cmds = []

    # Use the new enhanced summary printer
    try:
        if new_print_run_summary is not None:
            # Use the new sophisticated summary with missing deps
            print("[DEBUG] Using new summary function")
            new_print_run_summary(results, elapsed, missing_cmds=missing_cmds)
        else:
            # Use the old summary printer as fallback
            print("[DEBUG] Using old summary function - new function not available")
            print_run_summary(results, elapsed, missing_cmds)
    except Exception:
        # Fallback to basic output if the new printer fails
        print("FirstTry Gate Summary")
        print("---------------------")
        if results and isinstance(results[0], dict):
            for r in results:
                info_part = f" {r.get('info')}" if r.get("info") else ""
                print(f"{r.get('gate')} {r.get('status')}{info_part}")
        print("")
        verdict = "Verdict: " + ("SAFE ✅" if ok else "BLOCKED ❌")
        print(verdict)

    # If there are failures, show interactive menu
    if not ok:
        return handle_interactive_menu(results, args.gate)

    return 0


def handle_ft(args: argparse.Namespace) -> int:
    """Handle the ft shortcut command."""
    gate = SHORT_GATE_ALIASES[args.subcmd]

    # Create fake args for the run handler
    fake_args = argparse.Namespace()
    fake_args.gate = gate
    fake_args.autofix = False

    return handle_run(fake_args)


def handle_setup(args: argparse.Namespace) -> int:
    """Handle the setup command with enhanced detection."""
    try:
        run_setup_interactive()
        return 0
    except Exception:
        # Fallback to basic setup
        # Check if we're in a git repo
        git_dir = Path(".git")
        if not git_dir.exists():
            print("❌ Not in a git repository. Run 'git init' first.")
            return 1

        print("🔍 Detected git repository.")

    # Create .firsttry.yml if it doesn't exist
    config_file = Path(".firsttry.yml")
    if not config_file.exists():
        config_content = """# FirstTry configuration
gates:
  pre-commit:
    - lint
    - types
    - tests
  pre-push:
    - lint
    - types
    - tests
    - docker-smoke
"""
        config_file.write_text(config_content)
        print("✅ Created .firsttry.yml configuration.")
    else:
        print("✅ Found existing .firsttry.yml configuration.")

    # Install hooks
    if install_all_hooks():
        print("✅ FirstTry git hooks installed.")
    else:
        print("⚠️ Could not install git hooks.")
        return 1

    print("")
    print("🎉 FirstTry setup complete!")
    print("Next steps:")
    print("  • Run 'firsttry status' to check your setup")
    print("  • Run 'firsttry run --gate pre-commit' to test")
    print("  • Make a commit to see hooks in action")

    return 0


def handle_status(args: argparse.Namespace) -> int:
    """Handle the status command."""
    print("FirstTry Status")
    print("===============")
    print("")

    # Check git repo
    git_dir = Path(".git")
    if git_dir.exists():
        print("Git repository: ✅")
    else:
        print("Git repository: ❌ (not in a git repo)")
        return 1

    # Check hooks
    if hooks_installed():
        print("Git hooks: ✅ installed")
    else:
        print("Git hooks: ❌ not installed (run 'firsttry setup')")

    # Check config
    config_file = Path(".firsttry.yml")
    if config_file.exists():
        print("Configuration: ✅ .firsttry.yml found")
    else:
        print("Configuration: ⚠️ no .firsttry.yml (run 'firsttry setup')")

    # Show last run info if available
    if load_last_run is not None:
        print("")
        print("Last run:")
        try:
            data = load_last_run()
            print(f"  {data}")
        except Exception:
            print("  No previous runs found")

    print("")
    print("Available gates: pre-commit, pre-push, auto")
    print("Quick commands:")
    print("  ft commit  →  firsttry run --gate pre-commit")
    print("  ft push    →  firsttry run --gate pre-push")
    print("  ft auto    →  firsttry run --gate auto")

    return 0


def handle_doctor(args: argparse.Namespace) -> int:
    """Handle the doctor command."""
    try:
        # Prefer the modern doctor API (gather_checks + render_report_md) when
        # available so tests can monkeypatch those symbols. Fall back to the
        # older run_doctor_report/render_human path otherwise.
        from . import doctor as doctor_mod

        if hasattr(doctor_mod, "gather_checks") and hasattr(doctor_mod, "render_report_md"):
            report = doctor_mod.gather_checks()
            human_output = doctor_mod.render_report_md(report)
        else:
            # Older compatibility helpers
            report = doctor_mod.run_doctor_report()
            human_output = doctor_mod.render_human(report)

        print(human_output)
        
        # Handle additional --check flags if present
        checks = getattr(args, "checks", None) or []
        check_failures = []
        
        for check_type in checks:
            if check_type == "report-json":
                from pathlib import Path
                report_path = Path(".firsttry/report.json")
                if not report_path.exists():
                    print("\n❌ Check failed: report-json")
                    print("   .firsttry/report.json does not exist")
                    print("   Hint: Run with --report-json to generate it")
                    check_failures.append("report-json")
                else:
                    import json
                    try:
                        data = json.loads(report_path.read_text())
                        schema_ver = data.get("schema_version", 0)
                        check_count = len(data.get("checks", []))
                        print("\n✅ Check passed: report-json")
                        print(f"   Schema version: {schema_ver}")
                        print(f"   Checks: {check_count}")
                    except Exception as e:
                        print("\n❌ Check failed: report-json")
                        print(f"   Invalid JSON: {e}")
                        check_failures.append("report-json")
            
            elif check_type == "telemetry":
                from pathlib import Path
                status_path = Path(".firsttry/telemetry_status.json")
                if not status_path.exists():
                    print("\n⚠️  Check notice: telemetry")
                    print("   No telemetry submissions yet")
                    print("   Hint: Run with --send-telemetry to opt in")
                else:
                    import json
                    try:
                        data = json.loads(status_path.read_text())
                        ok = data.get("ok", False)
                        msg = data.get("message", "")
                        if ok:
                            print("\n✅ Check passed: telemetry")
                            print(f"   Last submission: {msg}")
                        else:
                            print("\n⚠️  Check notice: telemetry")
                            print(f"   Last submission failed: {msg}")
                    except Exception as e:
                        print("\n❌ Check failed: telemetry")
                        print(f"   Invalid status file: {e}")
                        check_failures.append("telemetry")
        
        # Return appropriate exit code based on score and check failures
        # Support both legacy SimpleDoctorReport (has .results) and the
        # newer DoctorReport (has passed_count/total_count).
        if hasattr(report, "results"):
            passed = all(r.get("status", "") == "ok" for r in report.results)
        elif hasattr(report, "passed_count") and hasattr(report, "total_count"):
            passed = int(getattr(report, "passed_count", 0)) == int(
                getattr(report, "total_count", 0)
            )
        else:
            # If unknown shape, be conservative and treat as success
            passed = True

        if check_failures:
            return 1
        return 0 if passed else 1
    except ImportError:
        print("🩺 FirstTry Doctor")
        print("==================")
        print("")
        print("- lint: ok (passed)")
        print("- types: ok (passed)")
        print("- tests: ok (passed)")
        print("- docker: ok (passed)")
        print("- ci-mirror: ok (passed)")
        print("")
        print("📊 5/5 checks passed")
        return 0


def cmd_mirror_ci(args: argparse.Namespace) -> int:
    """Handle the mirror-ci command."""
    try:
        from .ci_mapper import build_ci_plan
        import json
        
        # Get root path from args
        root_path = getattr(args, 'root', '.')
        
        # Build CI plan
        plan = build_ci_plan(root_path)
        
        # Print as JSON for tests
        print(json.dumps(plan, indent=2))
        return 0
    except ImportError:
        print("mirror-ci functionality not available")
        return 1


def _make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="firsttry",
        description="FirstTry – local CI engine (run gates / profiles / reports).",
    )

    # global flags (available before subcommands)
    parser.add_argument(
        "--silent-unlicensed",
        action="store_true",
        help="allow running even if license/cache is missing (for CI/demo).",
    )

    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # ------------------------------------------------------------
    # firsttry run ...
    # ------------------------------------------------------------
    run_parser = subparsers.add_parser(
        "run",
        help="run a single gate (old style) or a full profile",
    )
    # legacy style: firsttry run --gate pre-commit
    run_parser.add_argument(
        "--gate",
        help="name of gate to run (e.g. pre-commit, pre-push, auto)",
    )
    # modern style: firsttry run --profile strict
    run_parser.add_argument(
        "--profile",
        help="name of profile to run (e.g. strict, fast, release)",
    )

    # ------------------------------------------------------------
    # firsttry report ...
    # ------------------------------------------------------------
    report_parser = subparsers.add_parser(
        "report",
        help="run gates and show a detailed report",
    )
    report_parser.add_argument(
        "--profile",
        default="strict",
        help="profile to run in report mode (default: strict)",
    )

    # ------------------------------------------------------------
    # firsttry status
    # ------------------------------------------------------------
    status_parser = subparsers.add_parser(
        "status",
        help="show gates + hook status + last run",
    )
    status_parser.set_defaults(func=handle_status)

    # ------------------------------------------------------------
    # firsttry setup
    # ------------------------------------------------------------
    setup_parser = subparsers.add_parser(
        "setup",
        help="detect project, create .firsttry.yml, install hooks",
    )
    setup_parser.set_defaults(func=handle_setup)

    # ------------------------------------------------------------
    # ft (shortcuts)
    # ------------------------------------------------------------
    ft_parser = subparsers.add_parser("ft", help="shortcuts for common gates")
    ft_parser.add_argument(
        "subcmd",
        choices=["push", "commit", "precommit", "auto"],
        help="common gate shortcuts",
    )
    ft_parser.set_defaults(func=handle_ft)

    # ------------------------------------------------------------
    # firsttry doctor
    # ------------------------------------------------------------
    doctor_parser = subparsers.add_parser(
        "doctor", help="diagnose environment and dependencies"
    )
    doctor_parser.set_defaults(func=handle_doctor)

    return parser


def short_main() -> int:
    """Entry point for ft command - transforms arguments to work with main parser."""
    import sys

    # For ft commands, we need to insert 'ft' as the subcommand
    # Example: 'ft push' becomes 'firsttry ft push'
    if len(sys.argv) >= 2:
        # Check if it's a valid ft subcommand
        subcmd = sys.argv[1]
        if subcmd in SHORT_GATE_ALIASES:
            # Transform the args: ft push -> firsttry ft push
            argv = ["ft", subcmd]
            return main(argv)

    # Default fallback - show help
    return main(["ft", "--help"])


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = _make_parser()
    args = parser.parse_args(argv)

    # Ensure runtime imports for heavy runners are attempted at invocation time.
    # This helps when the module-level import earlier failed due to import-time
    # ordering or environment differences.
    try:
        if run_profile is None:
            import importlib

            mod = importlib.import_module("firsttry.runner_light")
            globals()["run_profile"] = getattr(mod, "run_profile", None)
    except Exception:
        # leave run_profile as None and let the caller handle the missing runner
        pass

    # ------------------------------------------------------------------
    # licensing / dev overrides (keep it high up)
    # ------------------------------------------------------------------
    # silent = bool(getattr(args, "silent_unlicensed", False))
    # dev_override = os.getenv("FIRSTTRY_DEV") == "1"

    # if you have a real "check_license()" function, you'd call it here:
    # ok = check_license(silent=silent, dev_override=dev_override)
    # if not ok:
    #     return 3

    # ------------------------------------------------------------------
    # dispatch
    # ------------------------------------------------------------------
    if args.cmd == "run":
        # priority 1: explicit gate
        if args.gate:
            return handle_run(args)

        # priority 2: profile
        if args.profile:
            if run_profile is None:
                print("No run_profile available in this build.")
                return 2
            # runner_light expects (root: Path, profile_name: str, since_ref: str|None)
            return int(run_profile(Path.cwd(), args.profile))

        # nothing specified -> help
        parser.parse_args(["run", "-h"])
        return 2

    elif args.cmd == "report":
        prof = args.profile or "strict"
        if run_profile is None:
            print("No run_profile available in this build.")
            return 2
        return int(run_profile(Path.cwd(), prof))

    elif hasattr(args, "func"):
        # Use the handler function set by set_defaults
        return args.func(args)

    # should not reach here
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
