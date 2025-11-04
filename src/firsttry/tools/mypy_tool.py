from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Tuple


class MypyTool:
    name = "mypy"
    phase = "slow"  # or "mutating" if you sequence it differently

    def __init__(self, repo_root: Path, targets: List[str] | None = None):
        self.repo_root = repo_root
        self.targets = targets or ["src"]

    def input_paths(self) -> List[str]:
        return [str(self.repo_root / t) for t in self.targets]

    def run(self) -> Tuple[str, Dict[str, Any]]:
        # 🔥 heavy import lives here
        import subprocess

        cmd = ["mypy"] + self.targets
        try:
            proc = subprocess.run(
                cmd, cwd=self.repo_root, capture_output=True, text=True
            )
        except FileNotFoundError:
            return "fail", {
                "stdout": "",
                "stderr": "mypy executable not found in PATH. Hint: pip install mypy or run: make dev",
            }

        if proc.returncode == 0:
            return "ok", {"stdout": proc.stdout, "stderr": proc.stderr}
        return "fail", {"stdout": proc.stdout, "stderr": proc.stderr}