from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple


def load_parity_lock(path: str = "ci/parity.lock.json") -> Dict:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def check_python_version_parity(lock: Dict) -> Tuple[bool, str]:
    expected = lock.get("python", {}).get("version")
    if not expected:
        return True, "no python version pinned"
    import sys

    actual = f"{sys.version_info.major}.{sys.version_info.minor}"
    ok = actual == expected
    msg = f"python: expected={expected} actual={actual}"
    return ok, msg


def check_tool_version_parity(lock: Dict) -> Tuple[bool, str]:
    # Very small heuristic: compare presence of top-level keys
    tools = lock.get("tools", {})
    if not tools:
        return True, "no tools pinned"
    # For demo: just report whether at least one tool is listed
    return True, f"tools pinned: {', '.join(tools.keys())}"


__all__ = ["load_parity_lock", "check_python_version_parity", "check_tool_version_parity"]
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Any

from ..ci_discovery.reader import discover_ci_jobs


class ToolVersionMismatchError(Exception):
    pass


class PythonVersionMismatchError(Exception):
    pass


def get_expected_tool_versions(lock_path: Path | None = None) -> Dict[str, str]:
    # prefer ci/parity.lock.json if present
    path = lock_path or Path("ci/parity.lock.json")
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except Exception:
        return {}

    tools = data.get("tools", {})
    out: Dict[str, str] = {}
    for k, v in tools.items():
        ver = v.get("version") if isinstance(v, dict) else None
        if ver:
            out[k] = ver
    return out


def get_local_tool_versions() -> Dict[str, str]:
    # Use importlib.metadata as parity runner uses
    import importlib.metadata

    tools = ["ruff", "mypy"]
    out: Dict[str, str] = {}
    for t in tools:
        try:
            out[t] = importlib.metadata.version(t)
        except importlib.metadata.PackageNotFoundError:
            out[t] = "not-installed"
    return out


def check_tool_version_parity(lock_path: Path | None = None) -> None:
    expected = get_expected_tool_versions(lock_path)
    local = get_local_tool_versions()

    mismatches = []
    for tool in ("ruff", "mypy"):
        exp = expected.get(tool)
        loc = local.get(tool)
        if exp and loc and exp != loc:
            mismatches.append((tool, exp, loc))

    if mismatches:
        lines = ["Environment parity check failed:"]
        for t, e, l in mismatches:
            lines.append(f"  - {t}: expected {e}, got {l}")
        raise ToolVersionMismatchError("\n".join(lines))


def get_expected_python_version(root: Path | None = None) -> str | None:
    # Discover python-version used by actions/setup-python in workflows
    jobs = discover_ci_jobs(root)
    for j in jobs:
        # search run_commands for setup-python uses or uses_actions
        for u in j.uses_actions:
            if "actions/setup-python" in u:
                # attempt to parse version from string like '@v4' not useful
                # look into run_commands for explicit with: python-version
                pass

    # Fallback: parse YAML files to find python-version more directly
    import yaml

    wf_root = Path(".github/workflows")
    if not wf_root.exists():
        return None

    for wf in sorted(wf_root.glob("*.yml")) + sorted(wf_root.glob("*.yaml")):
        try:
            doc = yaml.safe_load(wf.read_text()) or {}
        except Exception:
            continue

        jobs = doc.get("jobs") or {}
        for job in jobs.values():
            steps = job.get("steps") or []
            for s in steps:
                if isinstance(s, dict) and s.get("uses", "").startswith("actions/setup-python"):
                    w = s.get("with") or {}
                    pv = w.get("python-version") or w.get("python_version")
                    if pv:
                        # Normalize to major.minor
                        pv_str = str(pv)
                        if isinstance(pv, (list, tuple)):
                            pv_str = str(pv[0])
                        parts = pv_str.split(".")
                        if len(parts) >= 2:
                            return f"{parts[0]}.{parts[1]}"
                        return pv_str

    return None


def get_local_python_version() -> str:
    v = sys.version_info
    return f"{v.major}.{v.minor}"


def check_python_version_parity(root: Path | None = None) -> None:
    expected = get_expected_python_version(root)
    local = get_local_python_version()
    if expected and expected != local:
        raise PythonVersionMismatchError(
            f"Environment parity check failed:\n  - Python: expected {expected} (from CI), got {local}"
        )


__all__ = [
    "get_expected_tool_versions",
    "get_local_tool_versions",
    "check_tool_version_parity",
    "get_expected_python_version",
    "get_local_python_version",
    "check_python_version_parity",
    "ToolVersionMismatchError",
    "PythonVersionMismatchError",
]
