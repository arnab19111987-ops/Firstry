# src/firsttry/cache_utils.py
"""
High-performance cache utilities using stat-first validation.
Avoids expensive file hashing when possible by checking file metadata first.
"""

import os
from typing import List, Optional

from .cache_models import InputFileMeta, ToolCacheEntry, CacheStats


def collect_input_stats(paths: List[str]) -> Optional[List[InputFileMeta]]:
    """
    Collect file metadata (size, mtime) for cache validation.

    Returns None if any file is missing (forces re-run).
    This is the fast path - no file content hashing.
    """
    metas = []
    for p in paths:
        try:
            st = os.stat(p)
            metas.append(InputFileMeta(path=p, size=st.st_size, mtime=st.st_mtime))
        except FileNotFoundError:
            # File was removed -> force re-run
            return None
        except OSError:
            # Permission denied or other FS error -> force re-run
            return None
    return metas


def input_stats_match(
    cached: List[InputFileMeta], current: List[InputFileMeta]
) -> bool:
    """
    Fast comparison of file metadata without hashing.

    Returns True if all files have same size and mtime.
    This is ~1000x faster than computing SHA256 hashes.
    """
    if len(cached) != len(current):
        return False

    # Create lookup map for O(n) comparison
    cached_map = {f.path: f for f in cached}

    for cur in current:
        prev = cached_map.get(cur.path)
        if prev is None:
            return False
        if prev.size != cur.size or prev.mtime != cur.mtime:
            return False

    return True


def validate_cache_fast(cache_entry: ToolCacheEntry, input_paths: List[str]) -> bool:
    """
    Ultra-fast cache validation using only file stats.

    Returns True if cache is valid without any file hashing.
    This is the performance-critical path for warm cache hits.
    """
    if not cache_entry or not cache_entry.is_fresh():
        return False

    current_stats = collect_input_stats(input_paths)
    if current_stats is None:
        return False  # Missing files

    return input_stats_match(cache_entry.input_files, current_stats)


def get_cache_state(
    cache_entry: Optional[ToolCacheEntry],
    input_paths: List[str],
    policy_rerun_failures: bool = True,
) -> tuple[str, bool]:
    """
    Determine cache state and whether to use cached result.

    Returns (state, use_cache) where:
    - state: "hit" | "miss" | "policy-rerun" | "stale"
    - use_cache: whether to use cached result
    """
    if not cache_entry:
        return "miss", False

    if not cache_entry.is_fresh():
        return "stale", False

    # Fast stat-based validation
    if not validate_cache_fast(cache_entry, input_paths):
        return "miss", False

    # Cache is valid, but check failure policy
    if cache_entry.status == "fail" and policy_rerun_failures:
        return "policy-rerun", False

    return "hit", True


def update_cache_stats(stats: CacheStats, cache_state: str, used_hashing: bool = False):
    """Update cache statistics for reporting."""
    stats.total_tools += 1

    if cache_state == "hit":
        stats.cache_hits += 1
        stats.stat_checks += 1
    elif cache_state == "policy-rerun":
        stats.policy_reruns += 1
        stats.stat_checks += 1
    else:
        stats.cache_misses += 1
        if used_hashing:
            stats.hash_computations += 1
        else:
            stats.stat_checks += 1


def format_cache_report(stats: CacheStats) -> str:
    """Generate human-readable cache performance report."""
    lines = [
        "📊 Cache Performance:",
        f"  • Cache hits: {stats.cache_hits}/{stats.total_tools} ({stats.cache_efficiency:.1f}%)",
    ]

    if stats.policy_reruns > 0:
        lines.append(f"  • Policy re-runs: {stats.policy_reruns} (failed tools)")

    if stats.cache_misses > 0:
        lines.append(f"  • Cache misses: {stats.cache_misses} (new/changed files)")

    lines.append(f"  • Stat efficiency: {stats.stat_efficiency:.1f}% (avoided hashing)")

    return "\n".join(lines)
