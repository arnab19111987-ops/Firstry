# firsttry/executor.py
import shutil
import subprocess
from typing import Any


def run_command(cmd: str, cwd: str) -> dict:
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "ok": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "cmd": cmd,
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"{cmd} not found",
            "cmd": cmd,
        }


def execute_plan(
    plan: dict,
    autofix: bool = False,
    interactive_autofix: bool = True,
    max_tier=None,
) -> dict:
    root = plan["root"]
    summary: list[dict[str, Any]] = []
    all_ok = True

    # 1) sort steps by tier (1 first, then 2)
    steps = sorted(plan["steps"], key=lambda s: s.get("tier", 1))

    for step in steps:
        tier = step.get("tier", 1)
        if max_tier is not None and tier > max_tier:
            # skip higher tiers for now
            continue

        print(f"→ running [{step['id']}] tier={tier}", flush=True)
        step_ok = True
        step_results = []

        # run main commands
        for cmd in step["run"]:
            tool = cmd.split()[0]
            if shutil.which(tool) is None:
                step_results.append(
                    {
                        "ok": False,
                        "cmd": cmd,
                        "stderr": f"⚠️ Tool {tool} not found. Please install it.",
                        "stdout": "",
                    },
                )
                step_ok = False
                continue

            res = run_command(cmd, cwd=root)
            step_results.append(res)
            if not res["ok"]:
                step_ok = False

        fixed = []
        # try autofix if failed
        if (not step_ok) and step.get("autofix"):
            if autofix:
                for fix_cmd in step["autofix"]:
                    fix_res = run_command(fix_cmd, cwd=root)
                    fixed.append(fix_res)
                    if not fix_res["ok"]:
                        step_ok = False
            elif interactive_autofix:
                ans = (
                    input(f"⚠️ {step['id']} failed. Apply autofix commands? [Y/n]: ").strip().lower()
                )
                if ans in ("", "y", "yes"):
                    for fix_cmd in step["autofix"]:
                        fix_res = run_command(fix_cmd, cwd=root)
                        fixed.append(fix_res)
                        if not fix_res["ok"]:
                            step_ok = False

        summary.append(
            {
                "id": step["id"],
                "lang": step["lang"],
                "ok": step_ok,
                "results": step_results,
                "fixed": fixed,
            },
        )

        if not step_ok and not step.get("optional", False):
            all_ok = False

    return {
        "ok": all_ok,
        "summary": summary,
    }
