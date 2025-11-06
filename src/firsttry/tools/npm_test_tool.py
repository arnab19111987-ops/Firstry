from __future__ import annotations

from pathlib import Path
from typing import Any


class NpmTestTool:
    name = "npm-test"
    phase = "slow"

    def __init__(self, repo_root: Path, script: str = "test"):
        self.repo_root = repo_root
        self.script = script

    def input_paths(self) -> list[str]:
        return [str(self.repo_root / "package.json")]

    def run(self) -> tuple[str, dict[str, Any]]:
        import subprocess

        cmd = ["npm", "run", self.script, "--", "--color=false"]
        proc = subprocess.run(cmd, cwd=self.repo_root, capture_output=True, text=True, check=False)
        if proc.returncode == 0:
            return "ok", {"stdout": proc.stdout, "stderr": proc.stderr}
        return "fail", {"stdout": proc.stdout, "stderr": proc.stderr}
