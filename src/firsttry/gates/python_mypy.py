"""Python mypy gate implementation."""

import subprocess
from typing import Any

from .base import Gate
from .base import GateResult


class PythonMypyGate(Gate):
    """Gate that runs mypy type checking on Python code."""

    gate_id = "python_mypy"

    def run(self, project_root: Any | None = None) -> GateResult:
        """Run mypy type checking."""
        try:
            result = subprocess.run(
                ["mypy", "--ignore-missing-imports", "."],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )

            if result.returncode == 0:
                return GateResult(
                    gate_id=self.gate_id,
                    ok=True,
                    skipped=False,
                    reason="mypy type checking passed",
                )
            return GateResult(
                gate_id=self.gate_id,
                ok=False,
                skipped=False,
                reason=f"mypy found type errors:\n{result.stdout}\n{result.stderr}",
            )

        except FileNotFoundError:
            return GateResult(
                gate_id=self.gate_id,
                ok=True,
                skipped=True,
                reason="mypy not installed, skipping type checking",
            )
        except subprocess.TimeoutExpired:
            return GateResult(
                gate_id=self.gate_id,
                ok=False,
                skipped=False,
                reason="mypy type checking timed out",
            )
        except Exception as e:
            return GateResult(
                gate_id=self.gate_id,
                ok=False,
                skipped=False,
                reason=f"mypy error: {e}",
            )
