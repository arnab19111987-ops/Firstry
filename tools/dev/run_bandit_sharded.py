#!/usr/bin/env python3
# file: tools/dev/run_bandit_sharded.py
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, time
from pathlib import Path
from typing import List, Sequence

REPO = Path(__file__).resolve().parents[2]  # .../Firstry/tools/dev/ -> repo root


def _safe_run(cmd: Sequence[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), cwd=str(cwd) if cwd else None,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def _tracked_py_files(repo: Path) -> List[Path]:
    if shutil.which("git"):
        cp = _safe_run(["git", "ls-files", "*.py"], cwd=repo)
        if cp.returncode == 0:
            files = [repo / p for p in cp.stdout.splitlines() if p.strip()]
            if files:
                return files
    return list(repo.rglob("*.py"))


def _load_excludes(repo: Path) -> List[str]:
    try:
        # Use your existing helper
        sys.path.insert(0, str(repo / "src"))
        from firsttry.ignore import bandit_excludes  # type: ignore
        return bandit_excludes(repo)
    except Exception:
        # Conservative fallback
        defaults = [
            ".git",
            ".venv",
            ".venv-build",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "node_modules",
            "dist",
            "build",
            ".next",
            "coverage",
            ".firsttry",
            "__pycache__",
            "benchmarks",
            "snapshots",
        ]
        return [str(repo / d) for d in defaults]


def _filter_ignored(files: List[Path], excludes_abs: List[str]) -> List[Path]:
    excl_parts = [Path(p) for p in excludes_abs]
    def is_excluded(p: Path) -> bool:
        # Exclude if any excluded dir is in path parents
        for e in excl_parts:
            try:
                p.relative_to(e)
                return True
            except Exception:
                continue
        return False
    return [f for f in files if not is_excluded(f)]


def _chunk(items: List[Path], n: int) -> List[List[Path]]:
    n = max(1, n)
    out = [[] for _ in range(n)]
    # simple round-robin
    for i, it in enumerate(items):
        out[i % n].append(it)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=int(os.getenv("FT_BANDIT_JOBS", "2")))
    ap.add_argument("--outdir", default=str(REPO / ".firsttry" / "bandit_sharded"))
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    start_all = time.perf_counter()

    files = _tracked_py_files(REPO)
    excludes = _load_excludes(REPO)
    files = _filter_ignored(files, excludes)
    if not files:
        print("No Python files after filtering; nothing to scan.")
        return 0

    shards = _chunk(sorted(files), args.jobs)
    excl_arg = ",".join(excludes)

    merged = {"results": [], "errors": []}
    shard_times: List[float] = []

    for idx, shard in enumerate(shards, 1):
        if not shard:
            shard_times.append(0.0)
            continue
        shard_json = outdir / f"bandit_shard{idx}.json"
        cmd = ["bandit", "-q", "-f", "json"]
        if excl_arg:
            cmd += ["-x", excl_arg]
        cmd += [str(p) for p in shard]
        if args.verbose:
            print("CMD:", " ".join(cmd))

        t0 = time.perf_counter()
        cp = _safe_run(cmd, cwd=REPO)
        dt = time.perf_counter() - t0
        shard_times.append(dt)

        if cp.returncode not in (0, 1):  # bandit returns 1 when issues found
            print(f"[shard {idx}] bandit non-zero rc={cp.returncode}", file=sys.stderr)
        try:
            data = json.loads(cp.stdout.strip() or "{}")
        except Exception:
            data = {}
        (shard_json).write_text(json.dumps(data, indent=2))

        if isinstance(data, dict):
            merged["results"].extend(data.get("results", []))
            merged["errors"].extend(data.get("errors", []))

    merged_path = outdir / "bandit_merged.json"
    merged_path.write_text(json.dumps(merged, indent=2))
    total = time.perf_counter() - start_all

    print("\n== Bandit sharded summary ==")
    print(f"Shards        : {len(shards)}")
    print(f"Files scanned : {len(files)}")
    print(f"Excluded (-x) : {excl_arg[:160]}{'...' if len(excl_arg)>160 else ''}")
    for i, t in enumerate(shard_times, 1):
        print(f"  shard #{i:<2} : {t:0.2f}s")
    print(f"Total time    : {total:0.2f}s")
    print(f"Merged JSON   : {merged_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
