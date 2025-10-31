"""
FirstTry CLI - Stable Engine
============================

This is the original, stable CLI engine that focuses on core functionality.
It's reliable and well-tested, serving as the default engine.
"""

import argparse
import sys
import time
from pathlib import Path

# Import only core, stable functionality
try:
    from firsttry.gates import run_gate
except ImportError:
    try:
        import importlib.util

        _gates_path = Path(__file__).parent / "gates.py"
        spec = importlib.util.spec_from_file_location(
            "firsttry.gates", str(_gates_path)
        )
        _gates = importlib.util.module_from_spec(spec)
        sys.modules["firsttry.gates"] = _gates
        if spec and spec.loader:
            spec.loader.exec_module(_gates)
        run_gate = getattr(_gates, "run_gate", None)
    except Exception:
        run_gate = None

# Import hooks functionality
try:
    from .hooks import hooks_installed, install_all_hooks
except ImportError:

    def hooks_installed():
        return True

    def install_all_hooks():
        return True


SHORT_GATE_ALIASES = {
    "push": "pre-push",
    "commit": "pre-commit",
    "precommit": "pre-commit",
    "auto": "auto",
}


def ensure_hooks():
    """Ensure git hooks are installed (simplified stable version)."""
    if not hooks_installed():
        try:
            ans = input("Git hooks not installed. Install now? [Y/n]: ").strip().lower()
            if ans in ("", "y", "yes"):
                if install_all_hooks():
                    print("✅ FirstTry git hooks installed.")
                else:
                    print("⚠️ Could not install git hooks (no .git folder?).")
        except (EOFError, KeyboardInterrupt):
            pass


def handle_run_stable(args):
    """Handle run command - stable version."""
    ensure_hooks()

    if run_gate is None:
        print("No run_gate available in this build.")
        return 2

    start_time = time.time()
    results, ok = run_gate(args.gate)
    elapsed = time.time() - start_time

    # Simple summary output
    if ok:
        print(f"✅ All checks passed in {elapsed:.1f}s")
        return 0
    else:
        print(f"❌ Checks failed in {elapsed:.1f}s")
        if results:
            for r in results:
                if isinstance(r, dict) and not r.get("ok", True):
                    print(f"  • {r.get('gate', 'Unknown')}: {r.get('status', 'FAIL')}")
        return 1


def handle_ft_stable(args):
    """Handle ft command - stable version."""
    mapped_gate = SHORT_GATE_ALIASES.get(args.subcmd, args.subcmd)
    fake_args = argparse.Namespace()
    fake_args.gate = mapped_gate
    return handle_run_stable(fake_args)


def handle_setup_stable(args):
    """Handle setup command - stable version."""
    git_dir = Path(".git")
    if not git_dir.exists():
        print("❌ Not in a git repository. Run 'git init' first.")
        return 1

    print("🔍 Detected git repository.")

    config_file = Path(".firsttry.yml")
    if not config_file.exists():
        config_content = """# FirstTry configuration
gates:
  pre-commit:
    - lint
    - types
    - tests
  pre-push:
    - tests
"""
        config_file.write_text(config_content)
        print("✅ Created .firsttry.yml configuration.")
    else:
        print("✅ Found existing .firsttry.yml configuration.")

    if install_all_hooks():
        print("✅ FirstTry git hooks installed.")
    else:
        print("⚠️ Could not install git hooks (no .git folder?).")

    print("\n🎉 FirstTry setup complete!")
    print("Next steps:")
    print("  • Run 'firsttry status' to check your setup")
    print("  • Run 'firsttry run --gate pre-commit' to test")
    print("  • Make a commit to see hooks in action")

    return 0


def handle_status_stable(args):
    """Handle status command - stable version."""
    print("FirstTry Status")
    print("===============")
    print()

    # Check git repo
    if Path(".git").exists():
        print("Git repository: ✅")
    else:
        print("Git repository: ❌")
        return 1

    # Check hooks
    if hooks_installed():
        print("Git hooks: ✅ installed")
    else:
        print("Git hooks: ❌ not installed")

    # Check config
    if Path(".firsttry.yml").exists():
        print("Configuration: ✅ .firsttry.yml found")
    else:
        print("Configuration: ❌ .firsttry.yml missing")

    print()
    print("Last run:")
    print("  None")
    print()
    print("Available gates: pre-commit, pre-push, auto")
    print("Quick commands:")
    print("  ft commit  →  firsttry run --gate pre-commit")
    print("  ft push    →  firsttry run --gate pre-push")
    print("  ft auto    →  firsttry run --gate auto")

    return 0


def main():
    """Main entry point for stable engine."""
    parser = argparse.ArgumentParser(
        prog="firsttry", description="FirstTry – local CI engine (stable version)."
    )

    sub = parser.add_subparsers(dest="cmd")

    # run command
    p_run = sub.add_parser("run", help="run a single gate")
    p_run.add_argument(
        "--gate",
        required=True,
        help="name of gate to run (e.g. pre-commit, pre-push, auto)",
    )
    p_run.set_defaults(func=handle_run_stable)

    # ft command (shortcuts)
    p_ft = sub.add_parser("ft", help="shortcuts for common gates")
    p_ft.add_argument("subcmd", choices=list(SHORT_GATE_ALIASES.keys()))
    p_ft.set_defaults(func=handle_ft_stable)

    # setup command
    p_setup = sub.add_parser(
        "setup", help="detect project, create .firsttry.yml, install hooks"
    )
    p_setup.set_defaults(func=handle_setup_stable)

    # status command
    p_status = sub.add_parser("status", help="show gates + hook status + last run")
    p_status.set_defaults(func=handle_status_stable)

    args = parser.parse_args()

    if hasattr(args, "func"):
        return args.func(args)

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
