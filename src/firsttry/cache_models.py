# src/firsttry/cache_models.py
"""Advanced cache models using stat-first validation for maximum performance.
Avoids expensive file hashing when file metadata (size, mtime) hasn't changed.
"""

import json
import time
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class InputFileMeta:
    """Metadata for a single input file used in cache validation."""

    path: str
    size: int
    mtime: float  # last modified timestamp


@dataclass
class ToolCacheEntry:
    """Complete cache entry for a tool execution with stat-first validation."""

    tool_name: str
    input_files: list[InputFileMeta]
    input_hash: str  # sha256 of concatenated file hashes (fallback only)
    status: str  # "ok" | "fail"
    created_at: float
    extra: dict[str, Any]  # timing, output, etc.

    def to_json(self) -> str:
        """Serialize cache entry to JSON string."""
        return json.dumps(
            {
                "tool_name": self.tool_name,
                "input_files": [asdict(f) for f in self.input_files],
                "input_hash": self.input_hash,
                "status": self.status,
                "created_at": self.created_at,
                "extra": self.extra,
            },
            indent=2,
        )

    @staticmethod
    def from_json(raw: str) -> "ToolCacheEntry":
        """Deserialize cache entry from JSON string."""
        data = json.loads(raw)
        return ToolCacheEntry(
            tool_name=data["tool_name"],
            input_files=[InputFileMeta(**f) for f in data["input_files"]],
            input_hash=data["input_hash"],
            status=data["status"],
            created_at=data["created_at"],
            extra=data.get("extra", {}),
        )

    def is_fresh(self, max_age_hours: float = 24.0) -> bool:
        """Check if cache entry is within freshness window."""
        age_seconds = time.time() - self.created_at
        return age_seconds < (max_age_hours * 3600)

    def get_timing(self) -> float:
        """Get execution time from cache entry."""
        return self.extra.get("elapsed", 0.0)


@dataclass
class CacheStats:
    """Statistics for cache performance reporting."""

    total_tools: int = 0
    cache_hits: int = 0  # Files unchanged, used cached result
    policy_reruns: int = 0  # Re-ran failed tools by policy
    cache_misses: int = 0  # Actually new/changed inputs
    stat_checks: int = 0  # Fast stat-based validations
    hash_computations: int = 0  # Expensive hash computations

    @property
    def cache_efficiency(self) -> float:
        """Percentage of tools resolved without re-execution."""
        if self.total_tools == 0:
            return 0.0
        return (self.cache_hits / self.total_tools) * 100

    @property
    def stat_efficiency(self) -> float:
        """Percentage avoided expensive hashing via stat checks."""
        total_checks = self.stat_checks + self.hash_computations
        if total_checks == 0:
            return 0.0
        return (self.stat_checks / total_checks) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_tools": self.total_tools,
            "cache_hits": self.cache_hits,
            "policy_reruns": self.policy_reruns,
            "cache_misses": self.cache_misses,
            "cache_efficiency": round(self.cache_efficiency, 1),
            "stat_efficiency": round(self.stat_efficiency, 1),
        }
