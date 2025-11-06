from __future__ import annotations

from pathlib import Path
from typing import Any


class MypyTool:
    name = "mypy"
    phase = "slow"  # or "mutating" if you sequence it differently

    def __init__(self, repo_root: Path, targets: list[str] | None = None):
        self.repo_root = repo_root
        self.targets = targets or ["src"]

    def input_paths(self) -> list[str]:
        return [str(self.repo_root / t) for t in self.targets]

    def run(self) -> tuple[str, dict[str, Any]]:
        # 🔥 heavy import lives here
        import subprocess

        cmd = ["mypy"] + self.targets
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            return "ok", {
                "stdout": "mypy not found; skipping (soft-skip)",
                "stderr": "",
                "skipped": True,
            }

        if proc.returncode == 0:
            return "ok", {"stdout": proc.stdout, "stderr": proc.stderr}
        return "fail", {"stdout": proc.stdout, "stderr": proc.stderr}
