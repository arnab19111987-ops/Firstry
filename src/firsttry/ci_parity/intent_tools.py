from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import tomllib as toml

from .intents import get_intent, INTENT_REGISTRY


@dataclass
class StepLintIssue:
    plan: str
    step_id: str
    message: str


def infer_intent_from_run_cmd(run_cmd: str) -> Optional[str]:
    cmd = run_cmd.strip()

    if re.search(r"\bpytest\b", cmd):
        if "-k" in cmd or "fast" in cmd:
            return "tests_fast"
        return "tests_full"

    if re.search(r"\bruff\b", cmd):
        return "lint_fast"

    if re.search(r"\bmypy\b", cmd):
        return "typecheck"

    if "npm test" in cmd:
        return "node_tests"
    if "npm run lint" in cmd:
        return "node_lint"

    if "go test" in cmd:
        return "go_tests"

    if "terraform plan" in cmd:
        return "tf_plan"

    return None


def load_ci_mirror(path: Path) -> Dict[str, Any]:
    # Be tolerant with TOML parsing: prefer stdlib tomllib but fall back to
    # third-party `toml` which is more permissive for certain CI-discovery
    # multiline strings.
    try:
        with path.open("rb") as f:
            return toml.load(f)
    except Exception:
        try:
            import toml as _toml

            return _toml.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}


def save_ci_mirror(path: Path, data: Dict[str, Any]) -> None:
    # prefer tomli_w if available; fall back to basic write
    try:
        import tomli_w

        with path.open("wb") as f:
            tomli_w.dump(data, f)
        return
    except Exception:
        # naive fallback: write as repr (not ideal, but keeps the CLI usable)
        with path.open("w", encoding="utf8") as f:
            f.write(str(data))


def autofill_intents(mirror_path: Path) -> None:
    data = load_ci_mirror(mirror_path)

    plans = data.get("plans") or {}
    changed = False

    for plan_name, plan in plans.items():
        steps: Iterable[Dict[str, Any]] = plan.get("steps") or []
        for step in steps:
            if "intent" in step:
                continue
            run_cmd = step.get("run") or ""
            if not run_cmd.strip():
                continue

            inferred = infer_intent_from_run_cmd(run_cmd)
            if inferred and get_intent(inferred) is not None:
                step["intent"] = inferred
                changed = True

    if changed:
        save_ci_mirror(mirror_path, data)
        print(f"[firsttry] Updated intents in {mirror_path}")
    else:
        print(f"[firsttry] No intents to autofill in {mirror_path}")


def lint_intents(mirror_path: Path) -> List[StepLintIssue]:
    data = load_ci_mirror(mirror_path)
    plans = data.get("plans") or {}

    issues: List[StepLintIssue] = []

    for plan_name, plan in plans.items():
        steps: Iterable[Dict[str, Any]] = plan.get("steps") or []
        for step in steps:
            step_id = str(step.get("id") or step.get("name") or "<unnamed>")
            run_cmd = (step.get("run") or "").strip()
            if not run_cmd:
                continue

            inferred = infer_intent_from_run_cmd(run_cmd)
            if not inferred:
                continue

            if inferred not in INTENT_REGISTRY:
                continue

            if "intent" not in step:
                issues.append(
                    StepLintIssue(
                        plan=plan_name,
                        step_id=step_id,
                        message=(
                            f"Step '{step_id}' in plan '{plan_name}' uses '{run_cmd}' "
                            f"which matches intent '{inferred}' but has no 'intent' field."
                        ),
                    )
                )

    return issues


def cli_autofill_intents(mirror_path: str = ".firsttry/ci_mirror.toml") -> int:
    p = Path(mirror_path)
    autofill_intents(p)
    return 0


def cli_lint_intents(mirror_path: str = ".firsttry/ci_mirror.toml") -> int:
    p = Path(mirror_path)
    issues = lint_intents(p)
    if not issues:
        print("[firsttry] Intent lint: OK")
        return 0

    print("[firsttry] Intent lint: issues found:")
    for issue in issues:
        print(f"  - {issue.message}")
    return 1
