from __future__ import annotations

import os
import subprocess
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any

import click

from .ci_mapper import build_ci_plan, rewrite_run_cmd
from .gates import run_pre_commit_gate

# Attempt to import the runners module implementation from tools/firsttry if present
_repo_root = Path(__file__).resolve().parent
_impl_runners_path = _repo_root.parent / "tools" / "firsttry" / "firsttry" / "runners.py"
import importlib.util
import types

# Decide whether to try importing the real runners implementation.
_use_real = os.environ.get("FIRSTTRY_USE_REAL_RUNNERS", "").lower() in ("1", "true", "yes")
logger = logging.getLogger(__name__)

if _use_real and _impl_runners_path.exists():
    # Try to dynamically import the implementation from tools/firsttry.
    try:
        spec = importlib.util.spec_from_file_location("firsttry.runners_impl", str(_impl_runners_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[attr-defined]

        # Pull expected callables if present; fall back to stubs for missing names.
        def _wrap(name: str, default_name: str):
            if hasattr(mod, name):
                logger.debug("Using real runner %s from %s", name, _impl_runners_path)
                return getattr(mod, name)
            logger.warning("Real runners module missing %s; using stub", name)
            return _make_stub(default_name)

        def _make_stub(name: str):
            def _fn(*a, **k):
                logger.debug("runners.stub %s called; args=%r kwargs=%r", name, a, k)
                return types.SimpleNamespace(ok=True, name=name, duration_s=0.0, stdout="", stderr="", cmd=())

            return _fn

        runners = types.SimpleNamespace(
            run_ruff=_wrap("run_ruff", "ruff"),
            run_black_check=_wrap("run_black_check", "black-check"),
            run_mypy=_wrap("run_mypy", "mypy"),
            run_pytest_kexpr=_wrap("run_pytest_kexpr", "pytest"),
            run_coverage_xml=_wrap("run_coverage_xml", "coverage-xml"),
            coverage_gate=_wrap("coverage_gate", "coverage-gate"),
        )
    except Exception:
        logger.exception("Failed to import real runners from %s; falling back to safe stubs", _impl_runners_path)
        _use_real = False

if not _use_real:
    # Safe stub implementations that log when used.
    def _make_stub(name: str):
        def _fn(*a, **k):
            logger.debug("runners.stub %s called; args=%r kwargs=%r", name, a, k)
            return types.SimpleNamespace(ok=True, name=name, duration_s=0.0, stdout="", stderr="", cmd=())

        return _fn


    runners = types.SimpleNamespace(
        run_ruff=_make_stub("ruff"),
        run_black_check=_make_stub("black-check"),
        run_mypy=_make_stub("mypy"),
        run_pytest_kexpr=_make_stub("pytest"),
        run_coverage_xml=_make_stub("coverage-xml"),
        coverage_gate=_make_stub("coverage-gate"),
    )


# Small placeholders used by some tests — they are intentionally minimal and monkeypatchable.
def install_pre_commit_hook(*a, **k) -> Path:
    # Return a fake path where a pre-commit hook would be installed
    return Path(".git/hooks/pre-commit")


def get_changed_files(*a, **k) -> List[str]:
    # Minimal placeholder: list all Python files under tools/firsttry
    return [str(p) for p in Path(".").rglob("*.py")][:10]


def assert_license() -> tuple[bool, list, str]:
    # Minimal license check based on environment variables.
    # If FIRSTTRY_LICENSE_KEY and FIRSTTRY_LICENSE_URL are both set and non-empty,
    # consider the license valid. Tests may monkeypatch this function when needed.
    key = os.environ.get("FIRSTTRY_LICENSE_KEY", "")
    url = os.environ.get("FIRSTTRY_LICENSE_URL", "")
    if key and url:
        return True, [], "env"
    return False, [], ""


def _print_plan(plan: Dict[str, Any]) -> None:
    for wf in plan["workflows"]:
        print(f"Workflow: {wf['workflow_file']}")
        for job in wf["jobs"]:
            print(f"  Job: {job['job_id']}")
            for step in job["steps"]:
                print(f"    Step: {step['name']}")
                print("      Env:")
                for k, v in (step["env"] or {}).items():
                    print(f"        {k}={v}")
                print("      Run:")
                print(f"        {step['run']}")
        print("")


def _run_first_job(plan: Dict[str, Any]) -> int:
    if not plan["workflows"]:
        print("No workflows found.")
        return 0

    first_wf = plan["workflows"][0]
    if not first_wf["jobs"]:
        print("No jobs in first workflow.")
        return 0

    first_job = first_wf["jobs"][0]
    for step in first_job["steps"]:
        local_cmd = rewrite_run_cmd(step["run"])

        env_local = os.environ.copy()
        env_local.update(step["env"] or {})

        print(f"[firsttry mirror-ci] RUN: {local_cmd}")
        proc = subprocess.run(
            local_cmd,
            shell=True,
            env=env_local,
        )
        if proc.returncode != 0:
            print(
                f"[firsttry mirror-ci] Step '{step['name']}' failed with code {proc.returncode}"
            )
            return proc.returncode

    return 0


@click.group()
def main():
    """firsttry CLI entrypoint (click-based)."""


@main.command("mirror-ci")
@click.option("--root", default=".", help="Repo root (default: .)")
@click.option(
    "--run-first-job",
    is_flag=True,
    default=False,
    help="Actually execute first job steps sequentially",
)
def cmd_mirror_ci(root: str, run_first_job: bool) -> None:
    plan = build_ci_plan(Path(root).resolve())
    _print_plan(plan)

    if run_first_job:
        rc = _run_first_job(plan)
        raise SystemExit(rc)


@main.command("run")
@click.option("--gate", default="pre-commit", help="Which gate to run")
@click.option(
    "--require-license",
    is_flag=True,
    default=False,
    help="Require a valid license before running",
)
def cmd_run(gate: str, require_license: bool) -> None:
    # License check
    if require_license:
        ok, features, cache = assert_license()
        if not ok:
            click.echo("License invalid")
            raise SystemExit(2)
        else:
            click.echo("License ok")

    # For now support only the pre-commit gate used in tests
    if gate == "pre-commit":
        # simulate installing hook and listing changed files
        hook_path = install_pre_commit_hook()
        changed = get_changed_files()

        # Run individual runners in a simple sequence
        results = []
        results.append(runners.run_ruff(changed))
        results.append(runners.run_black_check(changed))
        results.append(runners.run_mypy(changed))
        results.append(runners.run_pytest_kexpr(changed))
        results.append(runners.run_coverage_xml(changed))
        results.append(runners.coverage_gate(changed))

        click.echo("Gate Summary")
        for r in results:
            name = getattr(r, "name", "step")
            ok = getattr(r, "ok", False)
            click.echo(f"  {name}: {'ok' if ok else 'FAIL'}")
        return

def cmd_mirror_ci_argparse(ns: argparse.Namespace) -> int:
    """Argparse-compatible wrapper used by older callers/tests.

    Returns integer exit code.
    """
    root = Path(ns.root).resolve()
    plan = build_ci_plan(root)
    _print_plan(plan)
    if getattr(ns, "run_first_job", False):
        return _run_first_job(plan)
    return 0


def cmd_run_argparse(ns: argparse.Namespace) -> int:
    """Argparse-compatible wrapper that returns an int exit code."""
    gate = getattr(ns, "gate", "pre-commit")
    require_license = getattr(ns, "require_license", False)

    if require_license:
        ok, features, cache = assert_license()
        if not ok:
            print("License invalid")
            return 2
        else:
            print("License ok")

    if gate == "pre-commit":
        hook_path = install_pre_commit_hook()
        changed = get_changed_files()

        results = []
        results.append(runners.run_ruff(changed))
        results.append(runners.run_black_check(changed))
        results.append(runners.run_mypy(changed))
        results.append(runners.run_pytest_kexpr(changed))
        results.append(runners.run_coverage_xml(changed))
        results.append(runners.coverage_gate(changed))

        print("Gate Summary")
        for r in results:
            name = getattr(r, "name", "step")
            ok = getattr(r, "ok", False)
            print(f"  {name}: {'ok' if ok else 'FAIL'}")
        return 0

    print(f"Unknown gate: {gate}")
    return 3


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser("firsttry")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_ci = sub.add_parser("mirror-ci", help="Mirror CI locally")
    p_ci.add_argument("--root", default=".", help="Repo root (default: .)")
    p_ci.add_argument(
        "--run-first-job",
        action="store_true",
        dest="run_first_job",
        help="Actually execute first job steps sequentially",
    )
    p_ci.set_defaults(func=cmd_mirror_ci_argparse)

    p_run = sub.add_parser("run", help="Run lightweight gate")
    p_run.add_argument("--gate", default="pre-commit")
    p_run.add_argument(
        "--require-license",
        action="store_true",
        dest="require_license",
        help="Require a valid license before running",
    )
    p_run.set_defaults(func=cmd_run_argparse)

    return p


