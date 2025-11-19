# firsttry/cli_pipelines.py
import argparse
import sys

from .executor import execute_plan
from .licensing import ensure_license_interactive
from .planner import build_plan
from .reporting import print_report
from .setup_wizard import run_setup


def build_parser():
    p = argparse.ArgumentParser(
        prog="firsttry", description="FirstTry — local CI engine"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Analyze repo and run all checks.")
    p_run.add_argument(
        "--autofix", action="store_true", help="Apply autofix where available."
    )
    p_run.add_argument("--root", default=".", help="Project root")
    p_run.add_argument("--no-license-prompt", action="store_true")

    sub.add_parser("setup", help="Interactive setup for this repo.")

    p_pc = sub.add_parser("precommit", help="Run pre-commit style gates.")
    p_pc.add_argument("--autofix", action="store_true")
    p_pc.add_argument("--root", default=".")
    p_pc.add_argument("--no-license-prompt", action="store_true")

    p_push = sub.add_parser("push", help="Run pre-push style gates.")
    p_push.add_argument("--autofix", action="store_true")
    p_push.add_argument("--root", default=".")
    p_push.add_argument("--no-license-prompt", action="store_true")

    return p


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)

    work_cmds = {"run", "precommit", "push"}

    if args.cmd in work_cmds and not getattr(args, "no_license_prompt", False):
        try:
            ensure_license_interactive()
        except SystemExit:
            print("Skipping license check for demo...")

    if args.cmd == "setup":
        run_setup()
        return 0

    if args.cmd in ("run", "precommit", "push"):
        plan = build_plan(root=args.root)
        report = execute_plan(plan, autofix=args.autofix, interactive_autofix=True)
        print_report(report)
        return 0 if report["ok"] else 1

    return 0


if __name__ == "__main__":
    main()
