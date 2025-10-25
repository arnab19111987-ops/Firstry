import os
import glob
from typing import Any, Dict, List, Optional

import yaml

# Heuristics for skipping or rewriting steps to make local run faster
# You can tune this list over time.
SKIP_KEYWORDS = [
    "actions/checkout",  # already in local workspace
    "actions/setup-python",  # we already have python locally
    "actions/setup-node",  # we already have node locally
    "actions/cache",  # caching is irrelevant locally
]

# Commands that are "setup / install" and usually slow.
# We'll keep them but mark them so runner can optionally group / dedupe them later.
INSTALL_HINTS = [
    "pip install",
    "pip3 install",
    "npm ci",
    "npm install",
    "pnpm install",
    "yarn install",
]


def _looks_like_setup_step(step: Dict[str, Any]) -> bool:
    """Determine if this step is mostly environment setup / install."""
    run_cmd = step.get("run", "") or ""
    if not run_cmd.strip():
        return False
    for kw in INSTALL_HINTS:
        if kw in run_cmd:
            return True
    return False


def _should_skip_step(step: Dict[str, Any]) -> bool:
    """Skip steps that don't matter locally (like setup actions)."""
    uses = step.get("uses")
    if uses:
        for bad in SKIP_KEYWORDS:
            if bad in str(uses):
                return True
    # Skip steps with no-op run
    run_cmd = step.get("run", "") or ""
    if not run_cmd.strip() and not uses:
        # nothing to do
        return True
    return False


def _collect_workflow_files(root: str) -> List[str]:
    pattern = os.path.join(root, ".github", "workflows", "*.yml")
    files = sorted(glob.glob(pattern))
    # also include .yaml
    pattern_yaml = pattern.replace(".yml", ".yaml")
    files += sorted(glob.glob(pattern_yaml))
    return files


def _safe_load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _normalize_step(
    step: Dict[str, Any], job_name: str, step_idx: int, wf_name: str
) -> Optional[Dict[str, Any]]:
    """
    Convert a GitHub Actions step into our internal fast plan step.

    Returns:
      {
        "job": "qa",
        "step_name": "Run tests",
        "cmd": "pytest -q",
        "install": False,
        "meta": { ... }  # source info for debugging
      }
    or None if skipped.
    """
    # Ignore useless steps
    if _should_skip_step(step):
        return None

    run_cmd = step.get("run", "") or ""
    step_name = step.get("name") or f"step-{step_idx}"

    # Tags for speed classification
    is_install = _looks_like_setup_step(step)

    return {
        "job": job_name,
        "step_name": step_name,
        "cmd": run_cmd.strip(),
        "install": is_install,
        "meta": {
            "workflow": wf_name,
            "job": job_name,
            "original_index": step_idx,
            "original_step": step,
        },
    }


def build_ci_plan(root: str) -> Dict[str, Any]:
    """
    Scan all workflows and build a local execution plan.

    Output shape:
    {
      "jobs": [
        {
          "job_name": "qa",
          "steps": [
             {
               "step_name": "Ruff Lint",
               "cmd": "ruff check .",
               "install": False,
               "meta": {...}
             },
             ...
          ]
        },
        ...
      ]
    }

    Notes:
    - We merge jobs across all workflows.
    - Steps that are skipped (like setup-python) are removed.
    - We keep order within each job.
    """
    workflows = _collect_workflow_files(root)
    jobs_out: List[Dict[str, Any]] = []
    workflows_out: List[Dict[str, Any]] = []

    for wf_path in workflows:
        wf_data = _safe_load_yaml(wf_path)
        wf_name = wf_data.get("name", os.path.basename(wf_path))
        wf_file = os.path.basename(wf_path)

        jobs_dict = wf_data.get("jobs", {}) or {}
        wf_jobs_legacy: List[Dict[str, Any]] = []

        for job_name, job_body in jobs_dict.items():
            raw_steps = job_body.get("steps", []) or []
            norm_steps: List[Dict[str, Any]] = []

            # legacy job shape: job_id and steps list with name/run/env
            legacy_steps: List[Dict[str, Any]] = []

            # job-level env that should be inherited by steps
            job_env = job_body.get("env", {}) or {}

            for idx, st in enumerate(raw_steps):
                # Build legacy step if it has a run
                if not _should_skip_step(st):
                    step_run = st.get("run", "") or ""
                    step_name = st.get("name") or f"step-{idx}"
                    step_env = dict(job_env)  # start with job env
                    step_env.update(st.get("env", {}) or {})

                    # Only include legacy step if it has a run command
                    if step_run.strip():
                        legacy_steps.append(
                            {
                                "name": step_name,
                                "run": step_run.strip(),
                                "env": step_env,
                            }
                        )

                # New normalized step
                norm = _normalize_step(
                    st, job_name=job_name, step_idx=idx, wf_name=wf_name
                )
                if norm is not None:
                    norm_steps.append(norm)

            # Only include the job if it has any actionable steps.
            if norm_steps:
                jobs_out.append(
                    {
                        "job_name": job_name,
                        "workflow_name": wf_name,
                        "steps": norm_steps,
                    }
                )

            # legacy job included if it has any steps
            if legacy_steps:
                wf_jobs_legacy.append({"job_id": job_name, "steps": legacy_steps})

        if wf_jobs_legacy:
            workflows_out.append({"workflow_file": wf_file, "jobs": wf_jobs_legacy})

    # Return both new 'jobs' shape and legacy 'workflows' shape for backwards compat
    out: Dict[str, Any] = {"jobs": jobs_out}
    if workflows_out:
        out["workflows"] = workflows_out
    return out


def rewrite_run_cmd(cmd: str, python_exe: Optional[str] = None) -> str:
    """Compatibility shim: optionally rewrite a run command for local execution.

    Current implementation is a no-op and returns the original command. In future
    this can rewrite matrix/docker steps to local equivalents.
    """
    import os
    import re

    py = python_exe or os.environ.get("FIRSTTRY_PYTHON")
    if not py:
        return cmd

    # Replace standalone 'python' or 'python3' tokens with the preferred interpreter
    out = re.sub(r"\bpython3?\b", py, cmd)

    # Replace 'pytest' invocations with 'PY -m pytest' so they run under the chosen interpreter
    # but avoid double-replacing when pytest already invoked via 'python -m pytest'
    out = re.sub(r"(?<!-m\s)\bpytest\b", f"{py} -m pytest", out)

    return out


# End of ci_mapper
