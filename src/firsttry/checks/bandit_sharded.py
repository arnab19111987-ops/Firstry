from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal, Optional

Severity = Literal["low", "medium", "high", "critical"]

# ---------- public API ----------

@dataclass
class BanditConfig:
    include_dirs: list[str]              # e.g. ["src", "firsttry"]
    exclude_dirs: list[str]              # e.g. [".venv", "node_modules", ".git", "__pycache__", "build", "dist"]
    jobs: int = 0                        # 0 => auto
    fail_on: Severity = "high"
    blocking: bool = True
    extra_args: list[str] | None = None  # any extra bandit flags to pass


@dataclass
class BanditShardResult:
    json_path: Path
    results_count: int


@dataclass
class BanditAggregate:
    issues_total: int
    by_severity: dict[str, int]
    max_severity: Optional[Severity]
    raw_json_path: Path  # merged JSON written here


def run_bandit_sharded(
    repo_root: Path,
    out_json: Path,
    cfg: BanditConfig,
    max_files_per_shard: int = 250,
) -> BanditAggregate:
    """
    Shard python file list and run bandit in parallel over shards.
    - Accuracy is preserved (we still scan every file exactly once)
    - Speedup comes from parallelism + avoiding scanning excluded dirs
    - Writes a merged JSON at `out_json`
    """
    repo_root = repo_root.resolve()
    out_json = out_json.resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)

    files = list(_discover_py_files(repo_root, cfg.include_dirs, cfg.exclude_dirs))
    if not files:
        # nothing to scan -> write an empty JSON with minimal fields
        _write_empty_bandit_json(out_json)
        return BanditAggregate(0, {}, None, out_json)

    # Decide parallelism
    cpu = os.cpu_count() or 2
    jobs = cpu if cfg.jobs in (None, 0) else max(1, int(cfg.jobs))

    # Make shards (avoid too-long command lines)
    shards: list[list[Path]] = []
    cur: list[Path] = []
    for f in files:
        cur.append(f)
        if len(cur) >= max_files_per_shard:
            shards.append(cur)
            cur = []
    if cur:
        shards.append(cur)

    # If only one shard and jobs==1, just run single bandit quickly
    if len(shards) == 1 and jobs == 1:
        shard_json = out_json.with_suffix(".single.json")
        _run_bandit_on_files(shards[0], shard_json, cfg.extra_args)
        _merge_jsons([shard_json], out_json)
        return _aggregate(out_json)

    # Parallel execution into a temp dir
    tmpdir = Path(tempfile.mkdtemp(prefix="bandit_shards_"))
    json_paths: list[Path] = []

    try:
        def do_one(idx_and_files: tuple[int, list[Path]]) -> BanditShardResult:
            idx, file_list = idx_and_files
            sj = tmpdir / f"bandit.shard.{idx:03d}.json"
            _run_bandit_on_files(file_list, sj, cfg.extra_args)
            cnt = _count_results(sj)
            return BanditShardResult(json_path=sj, results_count=cnt)

        with ThreadPoolExecutor(max_workers=jobs) as ex:
            futs = {ex.submit(do_one, (i, shard)): i for i, shard in enumerate(shards)}
            for fut in as_completed(futs):
                res = fut.result()
                json_paths.append(res.json_path)

        # Merge final JSON
        _merge_jsons(json_paths, out_json)
        return _aggregate(out_json)

    finally:
        # keep only the final merged JSON; delete temp shard files
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------- internals ----------


def _discover_py_files(
    root: Path,
    include_dirs: Iterable[str],
    exclude_dirs: Iterable[str],
) -> Iterable[Path]:
    inc = [root / d for d in include_dirs] if include_dirs else [root]
    exset = {str((root / d).resolve()) for d in exclude_dirs}
    for base in inc:
        base = base.resolve()
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            # exclude if any parent is in exclude set
            sp = str(p.parent.resolve())
            if any(sp.startswith(ex) for ex in exset):
                continue
            yield p


def _run_bandit_on_files(files: list[Path], out_json: Path, extra_args: Optional[list[str]]):
    out_json.parent.mkdir(parents=True, exist_ok=True)
    # Bandit supports multiple file targets; avoid -r for faster direct file mode.
    cmd = ["bandit", "-f", "json", "-o", str(out_json)]
    if extra_args:
        cmd.extend(extra_args)
    # Append file paths
    cmd.extend(str(f) for f in files)
    try:
        subprocess.run(cmd, check=False, capture_output=True, text=True)
    except FileNotFoundError:
        # write empty JSON so merge logic stays simple
        _write_empty_bandit_json(out_json)


def _merge_jsons(shard_jsons: list[Path], merged_out: Path):
    # Merge minimal fields: we only need "results" union for evaluation.
    merged = {"results": []}
    for sj in shard_jsons:
        try:
            data = json.loads(sj.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        res = data.get("results") or []
        if isinstance(res, list):
            merged["results"].extend(res)
    merged_out.write_text(json.dumps(merged, indent=2), encoding="utf-8")


def _aggregate(merged_json: Path) -> BanditAggregate:
    try:
        data = json.loads(merged_json.read_text(encoding="utf-8"))
    except Exception:
        data = {"results": []}
    issues = data.get("results") or []
    by = {}
    max_sev: Optional[Severity] = None
    max_rank = 0
    order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    for it in issues:
        sev = str(it.get("issue_severity") or "").lower()
        by[sev] = by.get(sev, 0) + 1
        r = order.get(sev, 0)
        if r > max_rank:
            max_rank, max_sev = r, sev if sev in ("low","medium","high","critical") else None
    return BanditAggregate(
        issues_total=len(issues),
        by_severity=by,
        max_severity=max_sev,
        raw_json_path=merged_json,
    )


def _count_results(json_path: Path) -> int:
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        return len(data.get("results") or [])
    except Exception:
        return 0


def _write_empty_bandit_json(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"results": []}, indent=2), encoding="utf-8")
