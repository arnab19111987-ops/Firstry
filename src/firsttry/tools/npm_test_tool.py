from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Tuple
import os
from firsttry.proc import run_cmd


class NpmTestTool:
    name = "npm-test"
    phase = "slow"

    def __init__(self, repo_root: Path, script: str = "test"):
        self.repo_root = repo_root
        self.script = script

    def input_paths(self) -> List[str]:
        # Cheap for the orchestrator to stat; avoids walking node_modules
        return [str(self.repo_root / "package.json")]

    def run(self) -> Tuple[str, Dict[str, Any]]:
        cmd = ["npm", "--silent", "run", self.script, "--", "--color=false"]

        # Safe env trims overhead; no behavior change to your tests.
        env = os.environ.copy()
        env["CI"] = "true"  # many CLIs reduce TTY noise/spinners in CI
        env["npm_config_update_notifier"] = "false"
        env["npm_config_audit"] = "false"
        env["npm_config_fund"] = "false"

        try:
            proc = run_cmd(
                cmd,
                cwd=self.repo_root,
                env=env,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return "fail", {
                "stdout": "",
                "stderr": "npm executable not found in PATH. Hint: install Node/npm or run: nvm install --lts",
            }

        status = "ok" if proc.returncode == 0 else "fail"
        return status, {"stdout": proc.stdout, "stderr": proc.stderr}
