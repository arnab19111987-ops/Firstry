from __future__ import annotations

import sys

from .planner import build_plan
from .util import run_step

USAGE = """Usage:
  python -m firsttry.ci_parity.runner pre-commit
  python -m firsttry.ci_parity.runner pre-push
  python -m firsttry.ci_parity.runner commit
  python -m firsttry.ci_parity.runner push
  python -m firsttry.ci_parity.runner ci
Env:
  FT_CI_PARITY_DRYRUN=1  # print commands without running them
"""


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if not argv or argv[0] not in {"pre-commit", "pre-push", "commit", "push", "ci"}:
        sys.stderr.write(USAGE)
        return 2
    profile = argv[0]
    plan = build_plan(profile)
    for step in plan.steps:
        rc, out = run_step(step)
        if out.strip():
            sys.stdout.write(out if out.endswith("\n") else out + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
