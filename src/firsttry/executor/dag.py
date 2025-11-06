from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Set, List, Optional
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, Future
from threading import Lock
from pathlib import Path
import time

from ..planner.dag import Plan
from ..runners.base import CheckRunner, RunResult
from ..runners.registry import default_registry
from ..cache.base import BaseCache, CacheHit
from ..cache.local import LocalCache
from ..cache.s3 import S3Cache


@dataclass
class TaskResult:
    id: str
    # outcome: "ok" | "fail" | "skip" | "error"
    status: str
    duration_ms: int
    # Normalized cache marker: None | "hit-local" | "hit-remote" | "miss-run"
    cache_status: Optional[str] = None
    # Can be bytes when coming from subprocess without text=True; accept both.
    stdout: str | bytes = ""
    stderr: str | bytes = ""
    cache_key: Optional[str] = None

    @property
    def is_cache_hit(self) -> bool:
        """Return True if this result was served from cache (local or remote)."""
        return (self.cache_status in ("hit-local", "hit-remote")) if getattr(self, "cache_status", None) is not None else (str(getattr(self, "status", "")).startswith("hit-"))

    def to_report_json(self) -> dict:
        cache_status = self.cache_status or "miss-run"

        def _to_str(x: str | bytes) -> str:
            if isinstance(x, bytes):
                try:
                    return x.decode("utf-8")
                except Exception:
                    return x.decode("utf-8", errors="backslashreplace")
            return x

        return {
            "name": self.id,
            "check_id": self.id,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "stdout": _to_str(self.stdout),
            "stderr": _to_str(self.stderr),
            "cache_status": cache_status,
        }


class DagExecutor:
    def __init__(
        self,
        repo_root: Path,
        plan: Plan,
        caches: List[BaseCache],
        runners: Dict[str, CheckRunner] | None = None,
        max_workers: int = 8,
        timeouts: Callable | None = None,
    ):
        self.repo_root = repo_root
        self.plan = plan
        self.caches = caches
        self.runners = runners or default_registry()
        self.max_workers = max_workers
        self.timeout_fn = timeouts or (lambda _check_id: 300)

        self.results: Dict[str, TaskResult] = {}
        self.dependents: Dict[str, Set[str]] = {}
        self.in_degree: Dict[str, int] = {}
        self.ready_queue: List[str] = []
        self.lock = Lock()

    def _build_graph(self):
        all_ids = set(self.plan.tasks.keys())
        for tid, t in self.plan.tasks.items():
            deps = t.deps.intersection(all_ids)
            self.in_degree[tid] = len(deps)
            if self.in_degree[tid] == 0:
                self.ready_queue.append(tid)
            for d in deps:
                self.dependents.setdefault(d, set()).add(tid)

    def _check_caches(self, key: str) -> Optional[TaskResult]:
        for idx, cache in enumerate(self.caches):
            hit = cache.get(key)
            if hit:
                cache_status = "hit-remote" if idx == 0 and len(self.caches) > 1 else "hit-local"
                return TaskResult(id="", status="ok", duration_ms=0, cache_status=cache_status, stdout=hit.stdout, stderr=hit.stderr, cache_key=key)
        return None

    def _store_success(self, key: str, rr: RunResult) -> None:
        payload = CacheHit(stdout=rr.stdout, stderr=rr.stderr, meta=rr.meta or {})
        for c in self.caches:
            try:
                c.put(key, payload)
            except Exception:
                pass

    def _execute(self, task_id: str) -> TaskResult:
        task = self.plan.tasks[task_id]
        runner = self.runners[task.check_id]
        start = time.monotonic()
        # 0) Zero-crash: verify tool exists before any work
        try:
            missing_msg = runner.prereq_check()
        except Exception:
            missing_msg = "prereq_check failed"
        if missing_msg:
            dur = int((time.monotonic() - start) * 1000)
            return TaskResult(
                id=task_id,
                status="skip",
                duration_ms=dur,
                stdout="",
                stderr=missing_msg,
                cache_key=None,
            )

        key = runner.build_cache_key(self.repo_root, task.targets, task.flags)

        cached = self._check_caches(key)
        if cached:
            cached.id = task_id
            cached.duration_ms = int((time.monotonic() - start) * 1000)
            cached.cache_key = key
            return cached
        # Respect per-check timeout: call runner.run with timeout_s kwarg
        timeout_s = int(self.timeout_fn(task.check_id))
        rr = runner.run(
            self.repo_root, task.targets, task.flags or [], timeout_s=timeout_s
        )
        dur = int((time.monotonic() - start) * 1000)
        # Normalize: status stays as outcome; cache_status marks this as a miss-run
        tr = TaskResult(id=task_id, status=rr.status, duration_ms=dur, cache_status="miss-run", stdout=rr.stdout, stderr=rr.stderr, cache_key=key)
        if rr.status == "ok":
            self._store_success(key, rr)
        return tr

    def _on_done(self, fut: Future):
        res: TaskResult = fut.result()
        with self.lock:
            self.results[res.id] = res
            for dep in self.dependents.get(res.id, set()):
                self.in_degree[dep] -= 1
                if self.in_degree[dep] == 0:
                    self.ready_queue.append(dep)

    def run(self) -> Dict[str, TaskResult]:
        self._build_graph()
        futures: Dict[str, Future] = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            while True:
                with self.lock:
                    while self.ready_queue:
                        t = self.ready_queue.pop(0)
                        if t not in futures:
                            f = pool.submit(self._execute, t)
                            f.add_done_callback(self._on_done)
                            futures[t] = f
                if len(self.results) == len(self.plan.tasks):
                    break
                time.sleep(0.01)
        return self.results


def default_caches(repo_root: Path, use_remote: bool) -> List[BaseCache]:
    caches: List[BaseCache] = []
    if use_remote:
        s3 = S3Cache.from_env()
        if s3:
            caches.append(s3)
    caches.append(LocalCache(repo_root))
    return caches
