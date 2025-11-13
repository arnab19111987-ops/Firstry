from __future__ import annotations

import time
import types
from collections.abc import Callable
from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from inspect import signature
from pathlib import Path
from threading import Lock
from typing import Any
from typing import Callable as _Callable
from typing import Sequence

from firsttry.planner.dag import Task
from firsttry.runner.executor import get_effective_timeout

from .. import runners as runners_module
from ..cache.base import BaseCache
from ..cache.base import CacheHit
from ..cache.local import LocalCache
from ..cache.s3 import S3Cache
from ..planner.dag import Plan
from ..runners.base import CheckRunner
from ..runners.base import RunResult
from ..runners.registry import default_registry


@dataclass
class TaskResult:
    id: str
    # outcome: "ok" | "fail" | "skip" | "error"
    status: str
    duration_ms: int
    # Normalized cache marker: None | "hit-local" | "hit-remote" | "miss-run"
    cache_status: str | None = None
    # Can be bytes when coming from subprocess without text=True; accept both.
    stdout: str | bytes = ""
    stderr: str | bytes = ""
    cache_key: str | None = None

    @property
    def is_cache_hit(self) -> bool:
        """Return True if this result was served from cache (local or remote)."""
        return (
            (self.cache_status in ("hit-local", "hit-remote"))
            if getattr(self, "cache_status", None) is not None
            else (str(getattr(self, "status", "")).startswith("hit-"))
        )

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
        caches: list[BaseCache],
        runners: dict[str, CheckRunner] | None = None,
        max_workers: int = 8,
        timeouts: Callable[[str], int] | None = None,
    ):
        self.repo_root = repo_root
        self.plan = plan
        self.caches = caches
        self.runners = runners or default_registry()
        self.max_workers = max_workers
        self.timeout_fn = timeouts or (lambda _check_id: 300)

        self.results: dict[str, TaskResult] = {}
        self.dependents: dict[str, set[str]] = {}
        self.in_degree: dict[str, int] = {}
        self.ready_queue: list[str] = []
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

    def _check_caches(self, key: str) -> TaskResult | None:
        for idx, cache in enumerate(self.caches):
            hit = cache.get(key)
            if hit:
                cache_status = "hit-remote" if idx == 0 and len(self.caches) > 1 else "hit-local"
                return TaskResult(
                    id="",
                    status="ok",
                    duration_ms=0,
                    cache_status=cache_status,
                    stdout=hit.stdout,
                    stderr=hit.stderr,
                    cache_key=key,
                )
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
        # Determine effective per-task timeout: prefer Task.timeout_s, else use timeout_fn
        # Keep existing behavior here for RunResult-producing runners. Some
        # tests exercise a small top-level helper `_call_runner_with_timeout`
        # (defined below) which normalizes return codes for simple runners.

        # Some runner implementations are adapters; for the lightweight
        # executor used by tests map well-known check_ids to the simple
        # runners in `firsttry.runners` to avoid signature mismatches.
        if task.check_id == "ruff":
            rr = _call_runner(runners_module.run_ruff, task.targets)
        elif task.check_id == "mypy":
            rr = _call_runner(runners_module.run_mypy, task.targets)
        elif task.check_id == "pytest":
            base = tuple(task.flags) if task.flags else ()
            rr = _call_runner(
                runners_module.run_pytest_files, task.targets, base_args=base, cwd=self.repo_root
            )
        elif task.check_id == "coverage":
            rr = _call_runner(runners_module.run_coverage_xml, self.repo_root)
        else:
            # Unknown check: synthesize a failing RunResult-like object
            rr = type(
                "R", (), {"status": "error", "stdout": "", "stderr": "unknown check", "meta": {}}
            )()
        dur = int((time.monotonic() - start) * 1000)
        # Normalize: status stays as outcome; cache_status marks this as a miss-run
        tr = TaskResult(
            id=task_id,
            status=rr.status,
            duration_ms=dur,
            cache_status="miss-run",
            stdout=rr.stdout,
            stderr=rr.stderr,
            cache_key=key,
        )
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

    def run(self) -> dict[str, TaskResult]:
        self._build_graph()
        futures: dict[str, Future] = {}
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
                # Deadlock safeguard: if there are no ready tasks and no
                # running futures but we still haven't produced results for
                # all tasks, mark the remaining tasks as errored and break.
                unfinished = [f for f in futures.values() if not f.done()]
                if (
                    not self.ready_queue
                    and not unfinished
                    and len(self.results) < len(self.plan.tasks)
                ):
                    remaining = set(self.plan.tasks.keys()) - set(self.results.keys())
                    for rid in remaining:
                        self.results[rid] = TaskResult(
                            id=rid,
                            status="error",
                            duration_ms=0,
                            stdout="",
                            stderr="unschedulable or cyclic dependency",
                        )
                    break
                time.sleep(0.01)
        return self.results


def _call_runner_with_timeout(
    runner: _Callable[..., Any],
    task: Task,
    *,
    cwd: str,
) -> int:
    """Call a runner with Task + cwd, passing timeout if supported.

    This keeps older runners compatible while letting new ones opt-in.
    Returns a normalized integer exit code.
    """
    timeout = get_effective_timeout(task)
    try:
        sig = signature(runner)
    except Exception:
        # If we can't introspect, just call and try to normalize.
        res = runner(task=task, cwd=cwd)  # type: ignore[misc]
        if isinstance(res, int):
            return res
        if hasattr(res, "returncode"):
            return int(getattr(res, "returncode"))
        if hasattr(res, "status"):
            return 0 if getattr(res, "status") == "ok" else 1
        return 0

    kwargs: dict[str, Any] = {"task": task, "cwd": cwd}
    if "timeout" in sig.parameters:
        kwargs["timeout"] = timeout
    elif "timeout_s" in sig.parameters:
        kwargs["timeout_s"] = timeout

    res = runner(**kwargs)
    if isinstance(res, int):
        return res
    if hasattr(res, "returncode"):
        return int(getattr(res, "returncode"))
    if hasattr(res, "status"):
        return 0 if getattr(res, "status") == "ok" else 1
    return 0


def _call_runner(
    fn: _Callable[..., Any],
    targets: Sequence[str] | Path | None = None,
    *,
    base_args: Sequence[str] | None = None,
    cwd: Path | str | None = None,
) -> Any:
    """Small adapter that calls a runner with targets + optional base args and cwd.

    This preserves compatibility with simple runner call signatures used in
    tests and in the lightweight executor.
    """
    # Normalize targets into a list when provided
    targs: list[str] | None
    if targets is None:
        targs = None
    elif isinstance(targets, (list, tuple)):
        targs = list(targets)
    else:
        # Path or single value
        targs = [str(targets)]

    kwargs: dict[str, Any] = {}
    if base_args:
        kwargs["base_args"] = list(base_args)
    if cwd is not None:
        kwargs["cwd"] = cwd

    # Common runner call patterns: fn(targets, base_args=..., cwd=...)
    # Call the runner with a couple of common signatures and normalize the
    # returned value into a RunResult-like object with attributes expected by
    # the DagExecutor (status, stdout, stderr, meta).
    try:
        if targs is None:
            res = fn(**kwargs)
        else:
            res = fn(targs, **kwargs)
    except TypeError:
        # Some runners accept `targets=` kwarg instead of positional targets.
        res = fn(targets=targs, **kwargs)

    # Normalize result into an object with `status`, `stdout`, `stderr`, `meta`.
    # Acceptable shapes include: int return codes, objects with `.returncode`,
    # objects with `.ok` boolean, or objects with `.status` string.
    stdout = getattr(res, "stdout", "")
    stderr = getattr(res, "stderr", "")
    meta = getattr(res, "meta", {})

    if isinstance(res, int):
        status = "ok" if res == 0 else "fail"
    elif hasattr(res, "returncode"):
        status = "ok" if int(getattr(res, "returncode")) == 0 else "fail"
    elif hasattr(res, "status"):
        status = getattr(res, "status")
    elif hasattr(res, "ok"):
        status = "ok" if getattr(res, "ok") else "fail"
    else:
        status = "error"

    return types.SimpleNamespace(status=status, stdout=stdout, stderr=stderr, meta=meta)


def default_caches(repo_root: Path, use_remote: bool) -> list[BaseCache]:
    caches: list[BaseCache] = []
    if use_remote:
        s3 = S3Cache.from_env()
        if s3:
            caches.append(s3)
    caches.append(LocalCache(repo_root))
    return caches
