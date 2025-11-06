"""Performance profiler for FirstTry checks.
Tracks timing and exit codes for all check executions.
"""

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any


@dataclass
class CheckTiming:
    """Timing information for a single check execution."""

    check_name: str
    family: str
    start_time: float
    end_time: float
    duration: float
    exit_code: int
    success: bool


class CheckProfiler:
    """Profiler that tracks timing for all check executions."""

    def __init__(self):
        self.timings: list[CheckTiming] = []
        self._active_checks: dict[str, float] = {}

    def start_check(self, check_name: str, family: str) -> None:
        """Start timing a check."""
        key = f"{family}:{check_name}"
        self._active_checks[key] = time.monotonic()

    def end_check(
        self,
        check_name: str,
        family: str,
        exit_code: int,
        success: bool,
    ) -> float:
        """End timing a check and record the result."""
        key = f"{family}:{check_name}"
        start_time = self._active_checks.pop(key, time.monotonic())
        end_time = time.monotonic()
        duration = end_time - start_time

        timing = CheckTiming(
            check_name=check_name,
            family=family,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            exit_code=exit_code,
            success=success,
        )

        self.timings.append(timing)
        return duration

    def get_timing_summary(self) -> dict[str, Any]:
        """Generate a timing summary by bucket/family."""
        if not self.timings:
            return {}

        # Group by family buckets
        fast_families = {"ruff", "mypy", "black"}
        slow_families = {"pytest", "npm test", "ci-parity"}

        buckets: dict[str, list[Any]] = {"fast": [], "slow": [], "other": []}

        for timing in self.timings:
            if timing.family in fast_families or timing.check_name in fast_families:
                buckets["fast"].append(timing)
            elif timing.family in slow_families or timing.check_name in slow_families:
                buckets["slow"].append(timing)
            else:
                buckets["other"].append(timing)

        summary = {}
        for bucket_name, timings in buckets.items():
            if timings:
                total_time = sum(t.duration for t in timings)
                details = {}

                # Group by check name for detailed breakdown
                by_check = defaultdict(list)
                for t in timings:
                    by_check[t.check_name].append(t)

                for check_name, check_timings in by_check.items():
                    check_total = sum(t.duration for t in check_timings)
                    details[check_name] = check_total

                summary[bucket_name] = {"total": total_time, "details": details}

        return summary

    def print_timing_summary(self) -> None:
        """Print a formatted timing summary."""
        summary = self.get_timing_summary()

        if not summary:
            return

        print("\n⏱️  Time split:")

        for bucket_name, bucket_data in summary.items():
            total = bucket_data["total"]
            details = bucket_data["details"]

            if total > 0:
                # Format main bucket line
                details_str = ", ".join(
                    [
                        f"{name}={dur:.1f}s"
                        for name, dur in sorted(
                            details.items(),
                            key=lambda x: x[1],
                            reverse=True,
                        )
                    ],
                )

                print(f"  {bucket_name}: {total:.1f}s ({details_str})")


# Global profiler instance
_profiler = CheckProfiler()


def get_profiler() -> CheckProfiler:
    """Get the global check profiler instance."""
    return _profiler


def reset_profiler() -> None:
    """Reset the global profiler for a new run."""
    global _profiler
    _profiler = CheckProfiler()
