"""Node.js test gate implementation."""

import subprocess
from pathlib import Path
from typing import Optional, Any
from .base import Gate, GateResult


class NodeNpmTestGate(Gate):
    """Gate that runs npm tests for Node.js projects."""
    
    gate_id = "node_tests"
    
    def run(self, project_root: Optional[Any] = None) -> GateResult:
        """Run npm tests."""
        try:
            # First check if package.json exists
            if project_root:
                package_json = Path(project_root) / "package.json"
            else:
                package_json = Path("package.json")
            if not package_json.exists():
                return GateResult(
                    gate_id=self.gate_id,
                    ok=True,
                    skipped=True,
                    reason="No package.json found, skipping npm tests"
                )
            
            result = subprocess.run(
                ["npm", "test"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                return GateResult(
                    gate_id=self.gate_id,
                    ok=True,
                    skipped=False,
                    reason="npm tests passed"
                )
            else:
                return GateResult(
                    gate_id=self.gate_id,
                    ok=False,
                    skipped=False,
                    reason=f"npm tests failed:\n{result.stdout}\n{result.stderr}"
                )
                
        except FileNotFoundError:
            return GateResult(
                gate_id=self.gate_id,
                ok=True,
                skipped=True,
                reason="npm not installed, skipping Node.js tests"
            )
        except subprocess.TimeoutExpired:
            return GateResult(
                gate_id=self.gate_id,
                ok=False,
                skipped=False,
                reason="npm tests timed out"
            )
        except Exception as e:
            return GateResult(
                gate_id=self.gate_id,
                ok=False,
                skipped=False,
                reason=f"npm test error: {e}"
            )