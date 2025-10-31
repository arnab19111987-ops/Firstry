"""Python linting gate implementation."""

import subprocess
from typing import Optional, Any
from .base import Gate, GateResult


class PythonRuffGate(Gate):
    """Gate that runs ruff linting on Python code."""
    
    gate_id = "python_lint"
    
    def run(self, project_root: Optional[Any] = None) -> GateResult:
        """Run ruff linting."""
        try:
            result = subprocess.run(
                ["ruff", "check", "."],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return GateResult(
                    gate_id=self.gate_id,
                    ok=True,
                    skipped=False,
                    reason="Ruff linting passed"
                )
            else:
                return GateResult(
                    gate_id=self.gate_id,
                    ok=False,
                    skipped=False,
                    reason=f"Ruff found issues:\n{result.stdout}"
                )
                
        except FileNotFoundError:
            return GateResult(
                gate_id=self.gate_id,
                ok=True,
                skipped=True,
                reason="ruff not installed, skipping Python linting"
            )
        except subprocess.TimeoutExpired:
            return GateResult(
                gate_id=self.gate_id,
                ok=False,
                skipped=False,
                reason="Ruff linting timed out"
            )
        except Exception as e:
            return GateResult(
                gate_id=self.gate_id,
                ok=False,
                skipped=False,
                reason=f"Ruff linting error: {e}"
            )