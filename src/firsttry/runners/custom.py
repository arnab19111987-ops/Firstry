from __future__ import annotations

from pathlib import Path

from .base import CheckRunner, RunResult


class CustomRunner(CheckRunner):
    check_id = "custom"

    def prereq_check(self) -> str | None:
        return None

    def build_cache_key(self, repo_root: Path, targets: list[str], flags: list[str]) -> str:
        return "ft-v1-custom-0"

    def run(
        self,
        repo_root: Path,
        files: list[str] | None = None,
        *,
        timeout_s: int | None = None,
    ) -> RunResult:
        # No-op placeholder; extend as needed
        return RunResult(name="custom", rc=0, stdout="", stderr="", duration_ms=0)
