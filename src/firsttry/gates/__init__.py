from .config import (
    CiMirrorConfig,
    Gate,
    Job,
    Plan,
    PolicyConfig,
    Step,
    load_ci_mirror,
    load_policy,
    resolve_jobs_for_gate,
)
from .deps import suggest_dependency_fix
from .runner import print_gate_summary, run_gate

__all__ = [
    "Step",
    "Plan",
    "Job",
    "Gate",
    "CiMirrorConfig",
    "PolicyConfig",
    "load_ci_mirror",
    "load_policy",
    "resolve_jobs_for_gate",
    "run_gate",
    "print_gate_summary",
    "suggest_dependency_fix",
]

# Back-compat: re-export legacy gate helpers from the compatibility module.
try:
    # Import legacy helpers from the moved file `gates_compat.py`.
    from ..gates_compat import *  # noqa: F401,F403 - re-export legacy names
except Exception:
    # If import fails, leave compatibility names absent — tests will fail clearly.
    pass

__all__.extend(
    [
        "run_pre_commit_gate",
        "run_pre_push_gate",
        "check_tests",
        "check_lint",
        "check_types",
        "GateResult",
        "gate_result_to_dict",
        "check_sqlite_drift",
        "check_pg_drift",
        "check_docker_smoke",
        "check_ci_mirror",
        "PRE_COMMIT_TASKS",
        "PRE_PUSH_TASKS",
        "run_gate",
        "run_all_gates",
        "format_summary",
        "print_verbose",
        "DEFAULT_GATES",
    ]
)
