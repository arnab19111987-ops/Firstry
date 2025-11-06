"""Go test gate implementation."""

import subprocess
from typing import Any

from .base import Gate
from .base import GateResult


class GoTestGate(Gate):
    """Gate that runs Go tests."""

    gate_id = "go_tests"

    def run(self, project_root: Any | None = None) -> GateResult:
        """Run Go tests."""
        try:
            result = subprocess.run(
                ["go", "test", "./..."],
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
                    reason="Go tests passed",
                )
            return GateResult(
                gate_id=self.gate_id,
                ok=False,
                skipped=False,
                reason=f"Go tests failed:\n{result.stdout}\n{result.stderr}",
            )

        except FileNotFoundError:
            return GateResult(
                gate_id=self.gate_id,
                ok=True,
                skipped=True,
                reason="go not installed, skipping Go tests",
            )
        except subprocess.TimeoutExpired:
            return GateResult(
                gate_id=self.gate_id,
                ok=False,
                skipped=False,
                reason="Go tests timed out",
            )
        except Exception as e:
            return GateResult(
                gate_id=self.gate_id,
                ok=False,
                skipped=False,
                reason=f"Go test error: {e}",
            )
