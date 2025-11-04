from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple


class RuffTool:
    name = "ruff"
    phase = "fast"  # used by orchestrator

    def __init__(self, repo_root: Path, extra_args: List[str] | None = None):
        self.repo_root = repo_root
        self.extra_args = extra_args or []

    def input_paths(self) -> List[str]:
        # keep it cheap; orchestrator may stat these
        return [str(self.repo_root / "src"), str(self.repo_root / "tests")]

    def run(self) -> Tuple[str, Dict[str, Any]]:
        # lazy import not strictly needed here
        cmd = ["ruff", "check", "."] + self.extra_args
        try:
            proc = subprocess.run(
                cmd, cwd=self.repo_root, capture_output=True, text=True
            )
        except FileNotFoundError:
            # Graceful failure if ruff isn't installed in PATH
            return "fail", {
                "stdout": "",
                "stderr": "ruff executable not found in PATH. Hint: pip install ruff or run: make dev",
            }

        if proc.returncode == 0:
            return "ok", {"stdout": proc.stdout, "stderr": proc.stderr}
        return "fail", {"stdout": proc.stdout, "stderr": proc.stderr}