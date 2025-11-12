from __future__ import annotations

from pathlib import Path

from .config import load_config, timeout_for, workflow_requires
from .executor.dag import DagExecutor, default_caches
from .planner.dag import Plan, build_plan_from_twin


def run_plan(
    repo_root: Path,
    plan: Plan,
    use_remote_cache: bool,
    workers: int = 8,
    *,
    tier: str | None = None,
    twin=None,
    changed_paths: list[str] | None = None,
    remote_cache_flag: bool = False,
):
    """Run a DAG Plan with config wiring.

    This function will:
      - load `firsttry.toml` from repo_root
      - merge per-check flags into tasks
      - build caches using config/flags
      - construct a timeout function from config
      - run `DagExecutor` with the provided plan

    Backwards compatible: if a `plan` is provided it will be used. If `twin` is
    provided (and `plan` is None) this will build the plan from the twin using
    config-derived `workflow_requires`.
    """
    repo_root = Path(repo_root).resolve()
    cfg = load_config(repo_root)

    # If caller passed a twin but not an explicit Plan, build the plan here
    if (not plan or (getattr(plan, "tasks", None) is None)) and twin is not None:
        plan = build_plan_from_twin(
            twin,
            tier=tier or "",
            changed=changed_paths or [],
            workflow_requires=workflow_requires(cfg),
            pytest_shards=1,
        )

    # Merge check-specific flags from config into Plan tasks
    if getattr(cfg, "checks_flags", None) and getattr(plan, "tasks", None):
        for t in plan.tasks.values():
            existing = t.flags or []
            cfg_flags = cfg.checks_flags.get(t.check_id, []) or []
            t.flags = list(cfg_flags) + list(existing)

    # Build caches (remote if enabled in config or via explicit flag)
    use_remote = bool(getattr(cfg, "remote_cache", False) or remote_cache_flag or use_remote_cache)
    caches = default_caches(repo_root, use_remote)

    # Timeouts: pull from config per check
    def timeout_fn(check_id: str) -> int:
        return timeout_for(cfg, check_id)

    executor = DagExecutor(
        repo_root=repo_root,
        plan=plan,
        caches=caches,
        max_workers=int(getattr(cfg, "workers", workers)),
        timeouts=timeout_fn,
    )

    results = executor.run()

    # TTY trust lines (use explicit cache_status now)
    for tid, r in results.items():
        prefix = "[CACHE]" if (r.cache_status or "").startswith("hit-") else "[ RUN ]"
        cs = r.cache_status or ""
        print(f"{prefix} {r.status.upper():10s} {tid} ({r.duration_ms}ms) {cs}")
    hits = sum(1 for r in results.values() if (r.cache_status or "").startswith("hit-"))
    ran = sum(1 for r in results.values() if not (r.cache_status or "").startswith("hit-"))
    print(f"\n{hits} checks verified from cache, {ran} run locally.\n")
    # Append to run history (one JSON line per run) for lightweight dashboards
    try:
        import json
        import time

        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tier": tier if "tier" in locals() else None,
            "checks": {
                k: {
                    "status": v.status,
                    "cache_status": v.cache_status,
                    "duration_ms": v.duration_ms,
                }
                for k, v in results.items()
            },
        }
        hist = repo_root / ".firsttry" / "history.jsonl"
        hist.parent.mkdir(parents=True, exist_ok=True)
        with hist.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        # best-effort; don't fail the run on history write problems
        pass
    return results
