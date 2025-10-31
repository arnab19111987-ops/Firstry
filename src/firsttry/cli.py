import argparse
from .orchestrator import run_unified, run_setup, show_status
from .hooks import install_git_hooks

LEVEL_TO_CHECKS = {
    "1": [
        "lint_basic",
        "autofix",
        "repo_sanity",
    ],
    "2": [
        "lint_basic",
        "autofix",
        "repo_sanity",
        "type_check_fast",
        "tests_fast",
        "env_deps_check",
    ],
    "3": [
        "lint_basic",
        "autofix",
        "repo_sanity",
        "type_check_fast",
        "tests_fast",
        "env_deps_check",
        "duplication_fast",
        "security_light",
        "coverage_warn",
        "conventions",
    ],
    "4": [
        "lint_basic",
        "autofix",
        "repo_sanity",
        "type_check_strict",
        "tests_full",
        "env_deps_check",
        "duplication_full",
        "security_full",
        "coverage_enforce",
        "migrations_drift",
        "deps_license",
    ],
}


def build_parser():
    p = argparse.ArgumentParser(prog="firsttry", description="FirstTry — Local CI that levels up with you")
    sub = p.add_subparsers(dest="cmd", required=True)

    # run
    p_run = sub.add_parser("run", help="Run checks (progressive levels of strictness)")
    p_run.add_argument(
        "--level",
        choices=["1", "2", "3", "4"],
        default="2",
        help="1=autofix basics, 2=types+tests, 3=team hygiene, 4=CI-grade",
    )

    # setup / activate / status
    sub.add_parser("activate", help="Activate your FirstTry license")
    sub.add_parser("status", help="Show current FirstTry status")
    sub.add_parser("install-hooks", help="Install Git hooks for auto-run")

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd == "run":
        selected = LEVEL_TO_CHECKS[args.level]
        print(f"🔹 Running FirstTry Level {args.level} — {len(selected)} checks")
        print("   (" + ", ".join(selected) + ")")

        success = run_unified(selected)
        if success:
            print(f"✅ Level {args.level} passed cleanly!")
            if args.level != "4":
                next_level = str(int(args.level) + 1)
                print(f"💡 Try `firsttry run --level {next_level}` for stricter tests.")
        else:
            print(f"❌ Level {args.level} failed. Fix above issues before pushing.")

    elif args.cmd == "activate":
        run_setup()
    elif args.cmd == "status":
        show_status()
    elif args.cmd == "install-hooks":
        try:
            install_git_hooks()
            print("✅ Git hooks installed successfully!")
            print("   • pre-commit: Level 2 (types + tests)")
            print("   • pre-push: Level 3 (team hygiene)")
        except Exception as e:
            print(f"❌ Failed to install git hooks: {e}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
