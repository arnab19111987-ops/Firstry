"""Security bandit gate implementation."""

import subprocess
from typing import Any

from .base import Gate
from .base import GateResult


class SecurityBanditGate(Gate):
    """Gate that runs bandit security scanning on Python code."""

    gate_id = "security_bandit"

    def run(self, project_root: Any | None = None) -> GateResult:
        """Run bandit security scanning."""
        try:
            result = subprocess.run(
                ["bandit", "-q", "-r", "."],
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
                    reason="bandit security scan passed",
                )
            return GateResult(
                gate_id=self.gate_id,
                ok=False,
                skipped=False,
                reason=f"bandit found security issues:\n{result.stdout}\n{result.stderr}",
            )

        except FileNotFoundError:
            return GateResult(
                gate_id=self.gate_id,
                ok=True,
                skipped=True,
                reason="bandit not installed, skipping security scan",
            )
        except subprocess.TimeoutExpired:
            return GateResult(
                gate_id=self.gate_id,
                ok=False,
                skipped=False,
                reason="bandit security scan timed out",
            )
        except Exception as e:
            return GateResult(
                gate_id=self.gate_id,
                ok=False,
                skipped=False,
                reason=f"bandit error: {e}",
            )
