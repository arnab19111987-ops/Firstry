"""Python pytest gate implementation."""

import subprocess
from typing import Optional, Any
from .base import Gate, GateResult


class PythonPytestGate(Gate):
    """Gate that runs pytest tests on Python code."""

    gate_id = "python_pytest"

    def run(self, project_root: Optional[Any] = None) -> GateResult:
        """Run pytest tests."""
        try:
            result = subprocess.run(
                ["pytest", "-q", "-m", "not slow"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                return GateResult(
                    gate_id=self.gate_id,
                    ok=True,
                    skipped=False,
                    reason="pytest tests passed",
                )
            else:
                return GateResult(
                    gate_id=self.gate_id,
                    ok=False,
                    skipped=False,
                    reason=f"pytest tests failed:\n{result.stdout}\n{result.stderr}",
                )

        except FileNotFoundError:
            return GateResult(
                gate_id=self.gate_id,
                ok=True,
                skipped=True,
                reason="pytest not installed, skipping tests",
            )
        except subprocess.TimeoutExpired:
            return GateResult(
                gate_id=self.gate_id,
                ok=False,
                skipped=False,
                reason="pytest tests timed out",
            )
        except Exception as e:
            return GateResult(
                gate_id=self.gate_id,
                ok=False,
                skipped=False,
                reason=f"pytest error: {e}",
            )
