from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict
from typing import List
from typing import Optional
from typing import TypedDict
from typing import Union

from .util import current_repo_root
from .util import normalize_cmd
from .util import tokenize_shell_line

TOOLS = (
    "black",
    "ruff",
    "mypy",
    "pytest",
    "bandit",
    "coverage",
    "codeql",
    "pyright",
    "safety",
    "python",
    "pip",
    "build",
)


class _CmdSpec(TypedDict):
    id: str
    cmd: List[str]


class _CovSpec(TypedDict):
    id: str
    threshold: int


DetectedStep = Union[_CmdSpec, _CovSpec]


@dataclass
class Detected:
    steps: List[DetectedStep]  # cmd specs and/or coverage threshold spec
    env: Dict[str, str]


def _scan_actions_runs() -> List[List[str]]:
    runs: List[List[str]] = []

    def _split_on_separators(tokens: List[str]) -> List[List[str]]:
        """Split a token list on shell command separators like &&, ; and ||."""
        out: List[List[str]] = []
        cur: List[str] = []
        for t in tokens:
            if t in ("&&", ";", "||"):
                if cur:
                    out.append(cur)
                cur = []
            else:
                cur.append(t)
        if cur:
            out.append(cur)
        return out

    for yml in (current_repo_root() / ".github" / "workflows").glob("*.yml"):
        lines = yml.read_text(encoding="utf-8", errors="ignore").splitlines()
        in_run = False
        buf: List[str] = []
        for ln in lines:
            # Match run: lines. Support both block (run: |) and single-line (run: pytest -q)
            m = re.match(r"^\s*(?:-\s*)?run\s*:\s*(\|?)(.*)$", ln)
            if m:
                rest = m.group(2) or ""
                if rest.strip():
                    # single-line run: capture the remainder immediately and split chained cmds
                    toks = normalize_cmd(tokenize_shell_line(rest.strip()))
                    for part in _split_on_separators(toks):
                        runs.append(part)
                    in_run = False
                    buf = []
                    continue
                # block-style run: start collecting the following indented lines
                in_run = True
                buf = []
                continue
            if in_run:
                # end collection when we hit a new top-level YAML key (job/steps/etc.)
                if re.match(r"^\s*[a-zA-Z0-9_-]+\s*:\s*", ln) and not ln.strip().startswith("-"):
                    if buf:
                        for b in buf:
                            toks = normalize_cmd(tokenize_shell_line(b))
                            for part in _split_on_separators(toks):
                                runs.append(part)
                    in_run = False
                else:
                    # strip YAML indentation
                    buf.append(ln.strip())
        if in_run and buf:
            for b in buf:
                toks = normalize_cmd(tokenize_shell_line(b))
                for part in _split_on_separators(toks):
                    runs.append(part)
    return runs


def _scan_pyproject() -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    # prefer stdlib tomllib
    try:
        import tomllib

        data = tomllib.loads((current_repo_root() / "pyproject.toml").read_text(encoding="utf-8"))
    except Exception:
        return out
    tool = data.get("tool", {})
    if "ruff" in tool:
        out["ruff"] = {"id": "ruff", "cmd": ["ruff", "check"]}
    if "black" in tool:
        out["black"] = {"id": "black", "cmd": ["black", "--check"]}
    if "mypy" in tool:
        out["mypy"] = {"id": "mypy", "cmd": ["mypy", "src"]}
    if "pytest" in tool:
        out["pytest"] = {"id": "pytest", "cmd": ["pytest", "-q"]}

    # coverage threshold in pyproject (commonly under [tool.coverage.report] fail_under)
    cov = tool.get("coverage", {})
    report = cov.get("report", {}) if isinstance(cov, dict) else {}
    fail_under = report.get("fail_under")
    if isinstance(fail_under, int):
        out["coverage-threshold"] = {"id": "coverage-threshold", "threshold": fail_under}
    return out


def _extract_cov_threshold_from_args(args: List[str]) -> Optional[int]:
    for i, a in enumerate(args):
        if a.startswith("--cov-fail-under="):
            try:
                return int(a.split("=", 1)[1])
            except ValueError:
                continue
        if a == "--cov-fail-under" and i + 1 < len(args):
            try:
                return int(args[i + 1])
            except ValueError:
                continue
    return None


def _is_runner_cmd(tokens: list[str]) -> bool:
    """True if command would invoke our own runner (avoid recursion)."""
    if not tokens:
        return False
    t0 = tokens[0]
    if t0 in {"python", "python3", "py"}:
        # look for: -m firsttry.ci_parity.runner <profile>
        for i in range(1, len(tokens) - 1):
            if tokens[i] == "-m" and tokens[i + 1] == "firsttry.ci_parity.runner":
                return True
    return False


def detect() -> Detected:
    steps: List[DetectedStep] = []
    env: Dict[str, str] = {}
    # From Actions YAML
    for cmd in _scan_actions_runs():
        if not cmd:
            continue
        # skip self-reference to avoid infinite recursion
        if _is_runner_cmd(cmd):
            continue
        t = cmd[0]
        # Special-case python -m pytest before generic tool matching
        if t == "python" and len(cmd) >= 3 and cmd[1] == "-m" and cmd[2] == "pytest":
            thr = _extract_cov_threshold_from_args(cmd)
            if thr is not None:
                steps.append({"id": "coverage-threshold", "threshold": thr})
            steps.append({"id": "pytest", "cmd": cmd})
            continue
        # Generic tools
        if t in TOOLS:
            # pytest may appear directly
            if t == "pytest":
                thr = _extract_cov_threshold_from_args(cmd)
                if thr is not None:
                    steps.append({"id": "coverage-threshold", "threshold": thr})
            steps.append({"id": t, "cmd": cmd})
    # From pyproject
    pj = _scan_pyproject()
    for _k, spec in pj.items():
        # coverage-threshold from pyproject may be present
        if spec.get("id") == "coverage-threshold":
            if not any(s.get("id") == "coverage-threshold" for s in steps):
                steps.append({"id": "coverage-threshold", "threshold": spec["threshold"]})
            continue
        tid = spec.get("id")
        if tid and not any(s["id"] == tid for s in steps):
            steps.append({"id": tid, "cmd": spec["cmd"]})
    # Sensible defaults if nothing found
    if not any(s["id"] == "black" for s in steps):
        if (current_repo_root() / "src").exists() or (current_repo_root() / "tests").exists():
            steps.append({"id": "black", "cmd": ["black", "--check", "src", "tests"]})
    if not any(s["id"] == "ruff" for s in steps):
        steps.append({"id": "ruff", "cmd": ["ruff", "check"]})
    if not any(s["id"] == "mypy" for s in steps) and (current_repo_root() / "src").exists():
        steps.append({"id": "mypy", "cmd": ["mypy", "src"]})
    if not any(s["id"] == "pytest" for s in steps) and (current_repo_root() / "tests").exists():
        steps.append({"id": "pytest", "cmd": ["pytest", "-q"]})
    # Enforce PYTHONPATH=src when src exists
    if (current_repo_root() / "src").exists():
        env["PYTHONPATH"] = "src"
    return Detected(steps=steps, env=env)


def load_user_overrides() -> Dict:
    """Optional overrides via firsttry.toml."""
    cfg = current_repo_root() / "firsttry.toml"
    if not cfg.exists():
        return {}
    try:
        import tomllib

        data = tomllib.loads(cfg.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data.get("firsttry", {})
