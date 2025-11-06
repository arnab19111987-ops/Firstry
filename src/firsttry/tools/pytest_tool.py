from __future__ import annotations

from pathlib import Path
from typing import Any


class PytestTool:
    name = "pytest"
    phase = "slow"

    def __init__(self, repo_root: Path, extra_args: list[str] | None = None):
        self.repo_root = repo_root
        self.extra_args = extra_args or []

    def input_paths(self) -> list[str]:
        return [str(self.repo_root / "src"), str(self.repo_root / "tests")]

    def run(self) -> tuple[str, dict[str, Any]]:
        # 🔥 heavy import lives here
        import subprocess

        cmd = ["pytest"] + self.extra_args
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
                "stdout": "pytest not found; skipping (soft-skip)",
                "stderr": "",
                "skipped": True,
            }

        if proc.returncode == 0:
            return "ok", {"stdout": proc.stdout, "stderr": proc.stderr}
        return "fail", {"stdout": proc.stdout, "stderr": proc.stderr}
