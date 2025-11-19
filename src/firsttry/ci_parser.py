# src/firsttry/ci_parser.py
from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any, Dict, Generator, List, Set

# hard dependency — tests run mypy on this file
import yaml

# -------------------- helpers -------------------- #


def _iter_ci_files(root: Path) -> Generator[Path, None, None]:
    gh = root / ".github" / "workflows"
    if gh.exists():
        yield from gh.glob("*.yml")
        yield from gh.glob("*.yaml")

    gl = root / ".gitlab-ci.yml"
    if gl.exists():
        yield gl

    circle = root / ".circleci" / "config.yml"
    if circle.exists():
        yield circle

    az = root / "azure-pipelines.yml"
    if az.exists():
        yield az

    jk = root / "Jenkinsfile"
    if jk.exists():
        yield jk


def _safe_load_yaml(path: Path) -> Dict[str, Any]:
    try:
        return yaml.safe_load(path.read_text()) or {}
    except Exception:
        return {}


def _extract_run_commands(step: Any) -> List[str]:
    if not isinstance(step, dict):
        return []
    run = step.get("run")
    if not run:
        return []
    lines: List[str] = []
    for line in str(run).splitlines():
        line = line.replace("&&", ";")
        for part in line.split(";"):
            part = part.strip()
            if part:
                lines.append(part)
    return lines


# -------------------- resolution helpers -------------------- #


def _family_from_tool(tool: str) -> str:
    tool = tool.lower()
    if tool in ("ruff", "flake8", "black", "eslint", "hadolint"):
        return "lint"
    if tool in ("mypy", "pyright", "tsc"):
        return "type"
    if tool in ("pytest", "npm test", "go test", "tox", "make:test"):
        return "tests"
    if tool in ("bandit", "safety", "pip-audit", "npm-audit"):
        return "security"
    return "custom"


def _resolve_tox(root: Path) -> List[Dict[str, str]]:
    """
    Try to read tox.ini and export real commands.
    If we can't, emit a generic tox step so parity can say
    "CI uses tox but we didn't mirror it".
    """
    tox_ini = root / "tox.ini"
    results: List[Dict[str, str]] = []
    if tox_ini.exists():
        text = tox_ini.read_text()
        cmd_lines: List[str] = []
        capture = False
        for line in text.splitlines():
            if line.strip().startswith("commands"):
                capture = True
                if "=" in line:
                    _, rhs = line.split("=", 1)
                    cmd_lines.append(rhs.strip())
                continue
            if capture:
                if line.strip().startswith("["):
                    break
                if not line.strip() or line.strip().startswith("#"):
                    continue
                cmd_lines.append(line.strip())

        for cl in cmd_lines:
            if not cl:
                continue
            results.append(
                {
                    "tool": _tool_from_command(cl, root) or "pytest",
                    "cmd": cl,
                    "family": _family_from_tool(
                        _tool_from_command(cl, root) or "pytest"
                    ),
                    "source": "ci:tox",
                }
            )
        if results:
            return results

    # fallback: tox but unknown commands
    results.append(
        {
            "tool": "tox",
            "cmd": "tox",
            "family": "tests",
            "source": "ci:tox",
        }
    )
    return results


def _resolve_make_test(root: Path) -> List[Dict[str, str]]:
    mk = root / "Makefile"
    if not mk.exists():
        return [
            {
                "tool": "make:test",
                "cmd": "make test",
                "family": "tests",
                "source": "ci:make",
            }
        ]
    text = mk.read_text()
    lines = text.splitlines()
    in_test = False
    cmds: List[str] = []
    for line in lines:
        if line.strip().startswith("test:"):
            in_test = True
            continue
        if in_test:
            if re.match(r"^[^\t]", line):
                break
            cmd = line.strip().lstrip("\t")
            if not cmd:
                continue
            cmds.append(cmd)
    out: List[Dict[str, str]] = []
    for c in cmds:
        tool = _tool_from_command(c, root) or "custom"
        out.append(
            {
                "tool": tool,
                "cmd": c,
                "family": _family_from_tool(tool),
                "source": "ci:make",
            }
        )
    return out or [
        {
            "tool": "make:test",
            "cmd": "make test",
            "family": "tests",
            "source": "ci:make",
        }
    ]


def _tool_from_command(cmd: str, root: Path) -> str | None:
    """
    Old detect_ci_tools used to stop here.
    We now keep the full command at higher level.
    """
    try:
        parts = shlex.split(cmd)
    except Exception:
        parts = cmd.split()

    if not parts:
        return None

    first = parts[0]

    # direct tools
    if first in (
        "ruff",
        "flake8",
        "black",
        "pytest",
        "mypy",
        "pyright",
        "bandit",
        "safety",
        "pip-audit",
    ):
        return first

    if first in ("npm", "yarn", "pnpm") and len(parts) > 1 and parts[1] == "test":
        return "npm test"

    if first == "go" and len(parts) > 1 and parts[1] == "test":
        return "go test"

    # meta-runners
    if first == "poetry" and len(parts) >= 3 and parts[1] == "run":
        return _tool_from_command(" ".join(parts[2:]), root)

    if first == "python" and len(parts) >= 3 and parts[1] == "-m":
        return _tool_from_command(" ".join(parts[2:]), root)

    if first == "tox":
        return "tox"

    if first == "make" and len(parts) >= 2 and parts[1] == "test":
        return "make:test"

    return None


# -------------------- PUBLIC API -------------------- #


def resolve_ci_plan(repo_root: str) -> List[Dict[str, str]] | None:
    """
    Return a CI-derived plan:
    [
      {"tool": "pytest", "cmd": "pytest -m 'not slow'", "family": "tests", "source": "ci:tox"},
      {"tool": "ruff", "cmd": "ruff .", "family": "lint", "source": "ci:gh-actions"},
    ]
    If no CI files, return None.
    """
    root = Path(repo_root)
    items: List[Dict[str, str]] = []

    for path in _iter_ci_files(root):
        data = _safe_load_yaml(path)
        jobs = data.get("jobs")
        if isinstance(jobs, dict):
            for job in jobs.values():
                if not isinstance(job, dict):
                    continue
                for step in job.get("steps", []):
                    for cmd in _extract_run_commands(step):
                        # meta-runners may produce many commands
                        # try to resolve special cases
                        try:
                            parts = shlex.split(cmd)
                        except Exception:
                            parts = cmd.split()

                        if parts and parts[0] == "tox":
                            items.extend(_resolve_tox(root))
                            continue
                        if (
                            parts
                            and parts[0] == "make"
                            and len(parts) >= 2
                            and parts[1] == "test"
                        ):
                            items.extend(_resolve_make_test(root))
                            continue

                        tool = _tool_from_command(cmd, root)
                        if tool:
                            items.append(
                                {
                                    "tool": tool,
                                    "cmd": cmd,
                                    "family": _family_from_tool(tool),
                                    "source": f"ci:{path.name}",
                                }
                            )
            continue

        # simple CI with top-level steps
        steps = data.get("steps")
        if isinstance(steps, list):
            for step in steps:
                for cmd in _extract_run_commands(step):
                    tool = _tool_from_command(cmd, root)
                    if tool:
                        items.append(
                            {
                                "tool": tool,
                                "cmd": cmd,
                                "family": _family_from_tool(tool),
                                "source": f"ci:{path.name}",
                            }
                        )

    return items or None


# backward compatibility (for anything still calling the old name)
def detect_ci_tools(repo_root: str) -> Set[str]:
    plan = resolve_ci_plan(repo_root) or []
    return {item["tool"] for item in plan}


def detect_ci_runtime(repo_root: str) -> Dict[str, str]:
    root = Path(repo_root)
    runtime: Dict[str, str] = {}

    for path in _iter_ci_files(root):
        data = _safe_load_yaml(path)
        jobs = data.get("jobs")
        if not isinstance(jobs, dict):
            continue
        for job in jobs.values():
            if not isinstance(job, dict):
                continue
            runs_on = job.get("runs-on") or ""
            if "ubuntu" in str(runs_on).lower():
                runtime.setdefault("os", "linux")
            steps = job.get("steps", [])
            for step in steps:
                if not isinstance(step, dict):
                    continue
                uses = step.get("uses") or ""
                if "actions/setup-python" in uses:
                    with_sec = step.get("with") or {}
                    py = with_sec.get("python-version")
                    if py:
                        runtime["python"] = str(py)
    return runtime


def detect_ci_deps(repo_root: str) -> Dict[str, str]:
    """
    Real CI often installs with: pip install -r requirements.txt
    We'll just detect the presence, and let deps_parity compare files.
    """
    root = Path(repo_root)
    req = root / "requirements.txt"
    if req.exists():
        # we don't know exact versions from CI, so return empty but flagged
        return {"requirements.txt": "*"}
    return {}
