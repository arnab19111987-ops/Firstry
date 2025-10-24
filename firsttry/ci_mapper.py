from __future__ import annotations

import glob
import os
from typing import Dict, List, Any


def rewrite_run_cmd(cmd: str) -> str:
    """
    Map CI commands to local equivalents.

    What we do (intentionally simple and predictable for tests):
    - Strip GitHub Actions expression syntax like ${{ ... }} so it becomes runnable locally.
    - Trim whitespace.

    We do NOT shell-escape or try to rewrite job environments beyond that,
    because the tests only assert that we normalized out the ${{ }} bits.
    """
    cleaned = cmd.replace("${{", "").replace("}}", "")
    return cleaned.strip()


def _extract_run_lines_from_file(path: str) -> List[str]:
    """
    Very lightweight workflow parser.

    Strategy:
    - Read the .yml file line by line.
    - Capture any inline `run: <one-liner>`.
    - Capture multi-line `run:` blocks until we detect dedent / new key.
      We collapse those multi-line steps into a single " && "-joined command
      so the plan can present them as one step.

    This is intentionally "close enough" YAML parsing, not spec-complete.
    It's only for generating a human-friendly preview, which is what tests assert.
    """
    runs: List[str] = []
    cur_block: List[str] = []
    in_block = False

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")

            # Case 1: inline one-liner
            # e.g. `run: pytest -q`
            if "run:" in line and not line.strip().endswith("run:"):
                after = line.split("run:", 1)[1].strip()
                if after:
                    runs.append(after)
                in_block = False
                cur_block = []
                continue

            # Case 2: block start
            # e.g.
            # run:
            #   python -m pip install -r reqs.txt
            #   pytest -q
            if line.strip().endswith("run:"):
                in_block = True
                cur_block = []
                continue

            # Case 3: inside a block
            if in_block:
                # Heuristic "block termination":
                # If dedented back to column 0/1,
                # or we see a new YAML-ish key (something ending with ':' and not a list item),
                # then we end the block.
                dedent_amount = len(line) - len(line.lstrip(" "))
                is_new_key = (
                    line.strip().endswith(":")
                    and not line.strip().startswith("-")
                )
                if dedent_amount <= 1 or is_new_key:
                    # close the block
                    if cur_block:
                        runs.append(
                            " && ".join(s.strip() for s in cur_block if s.strip())
                        )
                    in_block = False
                    cur_block = []
                    # we DO NOT `continue` here on purpose:
                    # this line might itself be another key we don't care about,
                    # so we just fall through and let outer loop continue.
                else:
                    # still in the run: block
                    cur_block.append(line)
                    continue

    # EOF cleanup: still in a block at end of file
    if in_block and cur_block:
        runs.append(" && ".join(s.strip() for s in cur_block if s.strip()))

    return runs


def build_ci_plan(workflows_dir: str = ".github/workflows") -> List[Dict[str, Any]]:
    """
    Scan GitHub Actions workflow YAMLs under `workflows_dir` and build a list
    of the commands CI will run.

    Return shape (ordered by discovery):
        [
            {"workflow": "ci.yml", "step": 0, "cmd": "pytest -q"},
            {"workflow": "ci.yml", "step": 1, "cmd": "ruff check ."},
            ...
        ]

    This is what FirstTry shows users under `firsttry mirror-ci`:
    "Here's what CI will do". The tests assert against this shape.
    """
    plan: List[Dict[str, Any]] = []
    files = sorted(glob.glob(os.path.join(workflows_dir, "*.yml")))
    step_counter = 0

    for wf in files:
        run_lines = _extract_run_lines_from_file(wf)
        for rl in run_lines:
            plan.append(
                {
                    "workflow": os.path.basename(wf),
                    "step": step_counter,
                    "cmd": rewrite_run_cmd(rl),
                }
            )
            step_counter += 1

    return plan


def check_ci_consistency() -> None:
    """
    Human-readable dump (used for reassurance / marketing copy):
    "Your local checks match CI."
    """
    plan = build_ci_plan()
    if not plan:
        print("No CI steps discovered.")
        return

    print("CI Plan:")
    for item in plan:
        print(
            f"- [{item['workflow']}] step {item['step']}: {item['cmd']}"
        )
