from __future__ import annotations

import os
from pathlib import Path

from firsttry.license_guard import maybe_download_golden_cache

from .config import get_config, get_s3_settings
from .executor.dag import DagExecutor, default_caches
from .planner.dag import Plan, build_plan_from_twin

# --- FirstTry: Pro-aware cache selection export (idempotent) ---


try:
    from .license_guard import get_current_tier
except Exception:  # fallback if import path differs

    def get_current_tier() -> str:
        return "free-lite"


# Provide minimal stubs only if your project doesn't already define them
if "LocalCache" not in globals():

    class LocalCache:
        def __init__(self, path: str | None = None):
            self.path = path or ".firsttry/warm"

        def __repr__(self) -> str:
            return f"<LocalCache path={self.path!r}>"


if "S3Cache" not in globals():

    class S3Cache:
        def __init__(self, bucket: str, prefix: str = "", region: str = ""):
            self.bucket = bucket
            self.prefix = prefix
            self.region = region

        @classmethod
        def from_env_or_config(cls):
            bucket = os.getenv("FT_S3_BUCKET") or os.getenv("FIRSTTRY_S3_BUCKET")
            if not bucket:
                return None
            prefix = os.getenv("FT_S3_PREFIX") or os.getenv("FIRSTTRY_S3_PREFIX") or ""
            region = os.getenv("AWS_REGION") or os.getenv("FIRSTTRY_AWS_REGION") or ""
            return cls(bucket=bucket, prefix=prefix, region=region)

        def __repr__(self) -> str:
            return f"<S3Cache bucket={self.bucket!r}>"


# Only define the export if not present already
if "get_caches_for_run" not in globals():

    def get_caches_for_run():
        """
        Returns the ordered list of caches for this run.
        Free: [LocalCache]
        Pro (and FT_S3_BUCKET set): [S3Cache, LocalCache]
        Pro (but no bucket): [LocalCache] with a warning
        """
        caches = [LocalCache()]
        if get_current_tier() == "pro":
            s3c = S3Cache.from_env_or_config()
            if s3c:
                print("🌐 Pro: Shared Remote Cache (S3) enabled.")
                caches.insert(0, s3c)
            else:
                print("⚠️ Pro Warning: FT_S3_BUCKET not set. Using local cache only.")
        return caches


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
    cfg = get_config(repo_root)

    # If caller passed a twin but not an explicit Plan, build the plan here
    if (not plan or (getattr(plan, "tasks", None) is None)) and twin is not None:
        plan = build_plan_from_twin(
            twin,
            tier=tier or "",
            changed=changed_paths or [],
            workflow_requires=cfg.workflow_requires,
            pytest_shards=1,
        )

    # Merge check-specific flags from config into Plan tasks. The new
    # centralized Config keeps raw TOML in `cfg.raw` so support both the
    # legacy dotted and underscored keys for backward compatibility.
    if getattr(plan, "tasks", None):
        try:
            cfg_flags_map = cfg.raw.get("checks_flags") or cfg.raw.get("checks.flags") or {}
        except Exception:
            cfg_flags_map = {}
        for t in plan.tasks.values():
            existing = list(t.flags or [])
            cfg_flags = list(cfg_flags_map.get(t.check_id, []) or [])
            if cfg_flags:
                t.flags = cfg_flags + existing

    # Build caches (remote if enabled in config or via explicit flag).
    # The new Config stores raw values under cfg.raw, so read [cache].remote
    try:
        cfg_cache_remote = bool(cfg.raw.get("cache", {}).get("remote", False))
    except Exception:
        cfg_cache_remote = False
    use_remote = bool(cfg_cache_remote or remote_cache_flag or use_remote_cache)

    # Pro-aware cache selection: local always available; Pro may enable S3 remote cache
    try:
        from firsttry.license_guard import get_current_tier
    except Exception:

        def get_current_tier() -> str:
            return "free-lite"

    class LocalCache:
        def __init__(self, path: str | None = None):
            self.path = path or ".firsttry/warm"

    class S3Cache:
        def __init__(self, bucket: str, prefix: str = "", region: str = ""):
            self.bucket = bucket
            self.prefix = prefix
            self.region = region

        @classmethod
        def from_env_or_config(cls):
            bucket = os.getenv("FT_S3_BUCKET") or os.getenv("FIRSTTRY_S3_BUCKET")
            if not bucket:
                return None
            prefix = os.getenv("FT_S3_PREFIX") or os.getenv("FIRSTTRY_S3_PREFIX") or ""
            region = os.getenv("AWS_REGION") or os.getenv("FIRSTTRY_AWS_REGION") or ""
            return cls(bucket=bucket, prefix=prefix, region=region)

    caches = default_caches(repo_root, use_remote)
    try:
        tier_now = get_current_tier()
        if tier_now == "pro":
            # Prefer explicit config S3 settings; fall back to env-based helper
            try:
                s3cfg = get_s3_settings(repo_root)
                if s3cfg and s3cfg.get("bucket"):
                    s3c = S3Cache(
                        s3cfg.get("bucket"),
                        prefix=s3cfg.get("prefix") or "",
                        region=s3cfg.get("region") or "",
                    )
                else:
                    s3c = S3Cache.from_env_or_config()
            except Exception:
                s3c = None

            if s3c:
                print("🌐 Pro: Shared Remote Cache (S3) enabled.")
                if isinstance(caches, list):
                    caches.insert(0, s3c)
            else:
                print("⚠️ Pro Warning: FT_S3_BUCKET not set. Using local cache only.")
    except Exception:
        # best-effort: don't fail on cache selection
        pass

    # Pro-only helper: best-effort golden cache download. Safe no-op on lite.
    try:
        maybe_download_golden_cache()
    except Exception:
        # never allow license helpers to break the run
        pass

    # Timeouts: pull from config per check (mirror legacy timeout_for)
    def timeout_fn(check_id: str) -> int:
        try:
            to = cfg.raw.get("timeouts", {}) or {}
            default = int(to.get("default", 300))
            per = to.get("per_check", {}) or {}
            return int(per.get(check_id, default))
        except Exception:
            return 300

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
