from __future__ import annotations

from pathlib import Path
from typing import Dict, Type, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from .profiles import GateProfile, get_profile
from .changes import get_changed_files
from .cache import load_cache, save_cache, should_skip_gate, update_gate_cache
from .reporting import print_summary

from .gates.base import Gate, GateResult
from .gates.python_lint import PythonRuffGate
from .gates.python_mypy import PythonMypyGate
from .gates.python_pytest import PythonPytestGate
from .gates.security_bandit import SecurityBanditGate
from .gates.drift_check import DriftCheckGate
from .gates.node_tests import NodeNpmTestGate
from .gates.go_tests import GoTestGate
from .gates.deps_lock import DepsLockGate
from .gates.coverage_check import CoverageCheckGate
from .gates.config_drift import ConfigDriftGate
from .gates.precommit_all import PreCommitAllGate
from .gates.ci_files_changed import CiFilesChangedGate
from .gates.env_tools import EnvToolsGate


# registry of known gates
GATE_REGISTRY: Dict[str, Type[Gate]] = {
    "python:ruff": PythonRuffGate,
    "python:mypy": PythonMypyGate,
    "python:pytest": PythonPytestGate,
    "security:bandit": SecurityBanditGate,
    "drift:check": DriftCheckGate,
    "node:npm": NodeNpmTestGate,
    "go:test": GoTestGate,
    # new gates
    "deps:lock": DepsLockGate,
    "coverage:check": CoverageCheckGate,
    "config:drift": ConfigDriftGate,
    "precommit:all": PreCommitAllGate,
    "ci:files": CiFilesChangedGate,
    "env:tools": EnvToolsGate,
}


def _instantiate(gate_id: str) -> Gate | None:
    cls = GATE_REGISTRY.get(gate_id)
    if not cls:
        return None
    return cls()


def run_profile(
    root: Path,
    profile_name: str = "fast",
    since_ref: str | None = None,
) -> int:
    profile: GateProfile = get_profile(profile_name)
    cache = load_cache(root)
    changed_files = get_changed_files(root, since_ref)

    results: List[GateResult] = []
    to_run: List[str] = []

    for gate_ref in profile.gates:
        optional = gate_ref.endswith("?")
        gate_id = gate_ref.rstrip("?")

        gate = _instantiate(gate_id)
        if not gate:
            if optional:
                results.append(
                    GateResult(
                        gate_id=gate_id,
                        ok=True,
                        skipped=True,
                        reason="gate not registered",
                    )
                )
            else:
                results.append(
                    GateResult(
                        gate_id=gate_id,
                        ok=False,
                        reason="gate not registered",
                    )
                )
            continue

        # adaptive: if we have changed files & gate doesn't care → skip
        if since_ref is not None and not gate.should_run_for(changed_files):
            results.append(
                GateResult(
                    gate_id=gate_id,
                    ok=True,
                    skipped=True,
                    reason="not impacted by changes",
                )
            )
            continue

        # cache-based skip
        if since_ref is not None and should_skip_gate(cache, gate_id, changed_files):
            results.append(
                GateResult(
                    gate_id=gate_id,
                    ok=True,
                    skipped=True,
                    reason="cached and unchanged",
                )
            )
            continue

        to_run.append(gate_id)

    # run remaining gates in parallel
    with ThreadPoolExecutor(max_workers=4) as ex:
        fut_map = {}
        for gate_id in to_run:
            gate = _instantiate(gate_id)
            fut = ex.submit(gate.run, root)
            fut_map[fut] = gate_id

        for fut in as_completed(fut_map):
            res: GateResult = fut.result()
            results.append(res)
            if res.ok and res.watched_files:
                update_gate_cache(cache, res.gate_id, res.watched_files)

    save_cache(root, cache)
    print_summary(results)

    # non-optional failures → exit 1
    return 0 if all(r.ok or r.skipped for r in results) else 1
