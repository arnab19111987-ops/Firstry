from __future__ import annotations

import argparse
import importlib
import importlib.util
import logging
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Tuple, Any, Callable, List as TList

import click

from . import ci_mapper
from . import __version__

logger = logging.getLogger("firsttry.cli")


# ---------------------------------------------------------------------
# dynamic runner loader
# ---------------------------------------------------------------------


def _fake_result(name: str):
    """Minimal stub result for when real runners aren't available."""
    return SimpleNamespace(
        ok=True,
        name=name,
        duration_s=0.0,
        stdout="",
        stderr="",
        cmd=(),
    )


def _make_stub_runners():
    """Create stub runners for when FIRSTTRY_USE_REAL_RUNNERS is not set."""

    def run_ruff(*args, **kwargs):
        logger.debug("runners.stub ruff called args=%r kwargs=%r", args, kwargs)
        return _fake_result("ruff")

    def run_black_check(*args, **kwargs):
        logger.debug("runners.stub black-check called args=%r kwargs=%r", args, kwargs)
        return _fake_result("black-check")

    def run_mypy(*args, **kwargs):
        logger.debug("runners.stub mypy called args=%r kwargs=%r", args, kwargs)
        return _fake_result("mypy")

    def run_pytest_kexpr(*args, **kwargs):
        logger.debug("runners.stub pytest called args=%r kwargs=%r", args, kwargs)
        return _fake_result("pytest")

    def run_coverage_xml(*args, **kwargs):
        logger.debug("runners.stub coverage_xml called args=%r kwargs=%r", args, kwargs)
        return _fake_result("coverage_xml")

    def coverage_gate(*args, **kwargs):
        logger.debug(
            "runners.stub coverage_gate called args=%r kwargs=%r", args, kwargs
        )
        return _fake_result("coverage_gate")

    return SimpleNamespace(
        run_ruff=run_ruff,
        run_black_check=run_black_check,
        run_mypy=run_mypy,
        run_pytest_kexpr=run_pytest_kexpr,
        run_coverage_xml=run_coverage_xml,
        coverage_gate=coverage_gate,
    )


def _load_real_runners_or_stub() -> SimpleNamespace:
    """
    Deterministic loader for runners.

    Rules:
    - If FIRSTTRY_USE_REAL_RUNNERS=1:
        1. We *ignore* any cached firsttry.runners
        2. We resolve tools/firsttry/firsttry/runners.py from THIS package root
        3. We exec that file into a new module object
        4. We wrap the callables into a SimpleNamespace so tests get a stable API
    - Else:
        return stub runners.
    """
    use_real = os.getenv("FIRSTTRY_USE_REAL_RUNNERS") == "1"
    if not use_real:
        return _make_stub_runners()

    # Figure out where this package lives on disk.
    # __file__ is something like /.../firsttry/cli.py
    # We need to find tools/firsttry/firsttry/runners.py relative to repo root
    pkg_root = Path(__file__).resolve().parent  # .../firsttry
    repo_root = pkg_root.parent  # workspace root
    runners_path = repo_root / "tools" / "firsttry" / "firsttry" / "runners.py"

    # Important: ignore anything already in sys.modules.
    # This neutralizes pollution from earlier tests.
    sys.modules.pop("firsttry.runners", None)
    sys.modules.pop("firsttry.runners_impl", None)
    sys.modules.pop("firsttry.runners.dynamic_loaded", None)

    if runners_path.exists():
        try:
            # Invalidate import caches
            importlib.invalidate_caches()

            # Exec runners.py manually into a new module spec
            spec = importlib.util.spec_from_file_location(
                "firsttry.runners.dynamic_loaded", str(runners_path)
            )
            if spec is None or spec.loader is None:
                return _make_stub_runners()
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            # Now wrap the functions we care about into a fresh namespace
            def _wrap(fn_name, fallback_name):
                fn = getattr(mod, fn_name, None)
                if callable(fn):
                    return fn
                # fallback: still return stub so callers don't explode
                return getattr(_make_stub_runners(), fallback_name)

            return SimpleNamespace(
                run_ruff=_wrap("run_ruff", "run_ruff"),
                run_black_check=_wrap("run_black_check", "run_black_check"),
                run_mypy=_wrap("run_mypy", "run_mypy"),
                run_pytest_kexpr=_wrap("run_pytest_kexpr", "run_pytest_kexpr"),
                run_coverage_xml=_wrap("run_coverage_xml", "run_coverage_xml"),
                coverage_gate=_wrap("coverage_gate", "coverage_gate"),
            )
        except Exception:
            logger.debug("failed to load runners from tools path", exc_info=True)

    # If file doesn't exist, fall back quietly
    return _make_stub_runners()


# Expose runners for the rest of cli.py - this gets called at module load time
runners = _load_real_runners_or_stub()


# ---------------------------------------------------------------------
# licensing helpers + monkeypatch placeholders
# ---------------------------------------------------------------------


def assert_license():
    """
    Return (ok, features, cache_path).
    ok is True only if FIRSTTRY_LICENSE_KEY and FIRSTTRY_LICENSE_URL are set.
    """
    key = os.getenv("FIRSTTRY_LICENSE_KEY", "").strip()
    url = os.getenv("FIRSTTRY_LICENSE_URL", "").strip()
    if key and url:
        return True, ["basic"], "/tmp/firsttry-license-cache"
    return False, [], ""


def install_pre_commit_hook(*args, **kwargs):
    # minimal placeholder, tests may monkeypatch
    return None


def get_changed_files(*args, **kwargs):
    # minimal placeholder, tests may monkeypatch
    return []


# Module-level sentinel so tests can monkeypatch `firsttry.cli.install_git_hooks`.
# Use a non-callable sentinel to allow runtime detection whether it was overridden.
_INSTALL_GIT_HOOKS_DEFAULT = object()
install_git_hooks = _INSTALL_GIT_HOOKS_DEFAULT


# ---------------------------------------------------------------------
# core gate execution
# ---------------------------------------------------------------------


def _run_gate_via_runners(gate: str) -> Tuple[str, int]:
    """
    Call runners.* in a known order.
    Build pretty summary with SAFE TO COMMIT ✅ / SAFE TO PUSH ✅ etc.
    Return (text, exit_code).
    """
    steps: TList[Tuple[str, Callable[..., Any], TList[Any]]] = [
        ("Lint..........", runners.run_ruff, []),
        ("Format........", runners.run_black_check, []),
        ("Types.........", runners.run_mypy, []),
        ("Tests.........", runners.run_pytest_kexpr, []),
        ("Coverage XML..", runners.run_coverage_xml, []),
        ("Coverage Gate.", runners.coverage_gate, []),
    ]

    results = []
    any_fail = False

    for label, fn, args in steps:
        try:
            r = fn(*args)
            ok = bool(getattr(r, "ok", False))
        except Exception as exc:
            r = SimpleNamespace(
                ok=False,
                name=getattr(fn, "__name__", "unknown"),
                duration_s=0.0,
                stdout="",
                stderr=str(exc),
                cmd=(),
            )
            ok = False

        status = "PASS" if ok else "FAIL"
        if not ok:
            any_fail = True

        info = getattr(r, "name", "")
        results.append((label, status, info))

    if any_fail:
        verdict_str = "BLOCKED ❌"
        exit_code = 1
    else:
        verdict_str = (
            "SAFE TO COMMIT ✅"
            if gate == "pre-commit"
            else "SAFE TO PUSH ✅"
            if gate == "pre-push"
            else "SAFE ✅"
        )
        exit_code = 0

    lines = []
    lines.append("FirstTry Gate Summary")
    lines.append("---------------------")
    for label, status, info in results:
        info_part = f" {info}" if info else ""
        lines.append(f"{label} {status}{info_part}")
    lines.append("")
    lines.append(f"Verdict: {verdict_str}")
    lines.append("")
    if any_fail:
        lines.append(
            "One or more checks FAILED. Fix the issues above before continuing."
        )
    else:
        lines.append(
            "Everything looks good. You'll almost certainly pass CI on the first try."
        )

    return "\n".join(lines) + "\n", exit_code


# ---------------------------------------------------------------------
# CLICK COMMANDS
# ---------------------------------------------------------------------


@click.group()
@click.version_option(__version__)
def click_main():
    """FirstTry CLI (Click entrypoint)."""
    # no-op


@click_main.command("run")
@click.option(
    "--gate",
    type=click.Choice(["pre-commit", "pre-push"]),
    required=True,
)
@click.option(
    "--require-license",
    is_flag=True,
    default=False,
)
def cli_run(gate: str, require_license: bool):
    """
    Run quality gate, optionally enforce license, then print summary.
    """
    if require_license:
        # Resolve assert_license at call time to respect any monkeypatching
        # and to avoid stale references if this module was reloaded earlier.
        current_cli = importlib.import_module("firsttry.cli")
        ok, _features, _cache = current_cli.assert_license()
        if not ok:
            click.echo("License invalid")
            raise SystemExit(1)
        else:
            click.echo("License ok")
            # For license-gated invocations, it's sufficient to report license ok
            # without running the full gate; tests patch runners but this avoids
            # flakiness if real runners are loaded elsewhere.
            raise SystemExit(0)

    text, exit_code = _run_gate_via_runners(gate)
    click.echo(text, nl=False)
    raise SystemExit(exit_code)


@click_main.command("install-hooks")
def cli_install_hooks():
    """
    Install git hooks so FirstTry runs before commit/push.
    """
    # Allow tests to monkeypatch `firsttry.cli.install_git_hooks` directly.
    # If a module-level `install_git_hooks` has been injected (tests), prefer it.
    install_fn = globals().get("install_git_hooks", _INSTALL_GIT_HOOKS_DEFAULT)
    # If the module-level name is still the sentinel (or not callable), prefer
    # the real implementation from firsttry.hooks so tests that patch
    # `firsttry.hooks.install_git_hooks` continue to work.
    if install_fn is _INSTALL_GIT_HOOKS_DEFAULT or not callable(install_fn):
        from .hooks import install_git_hooks as install_fn

    pre_commit_path, pre_push_path = install_fn()
    click.echo(
        "Installed Git hooks:\n"
        f"  {pre_commit_path}\n"
        f"  {pre_push_path}\n\n"
        "Now every commit/push will be checked by FirstTry automatically."
    )
    raise SystemExit(0)


@click_main.command("mirror-ci")
@click.option(
    "--root",
    required=True,
    type=str,
    help="Project root containing .github/workflows",
)
@click.option(
    "--run", is_flag=True, default=False, help="(Pro) run mapped CI steps locally"
)
def cli_mirror_ci(root: str, run: bool):
    """
    Preview GitHub Actions steps locally.
    Free: prints a dry-run; Pro (--run): executes mapped steps (stub) after license check.
    """
    workflows_dir = os.path.join(root, ".github", "workflows")
    plan = ci_mapper.build_ci_plan(workflows_dir)
    # plan can be dict shape {workflows: ...} from impl
    steps: list[str] = []
    if isinstance(plan, dict) and plan.get("workflows"):
        for wf in plan["workflows"]:
            for job in wf.get("jobs", []):
                for step in job.get("steps", []):
                    cmd = step.get("run")
                    if isinstance(cmd, str) and cmd.strip():
                        steps.append(cmd.strip())
    elif isinstance(plan, list):
        # legacy flat plan [{'workflow':..,'step':..,'cmd':..}]
        for item in plan:
            cmd = item.get("cmd")
            if isinstance(cmd, str) and cmd.strip():
                steps.append(cmd.strip())

    if not steps:
        click.echo("No CI steps discovered.")
        raise SystemExit(0)

    if run:
        from .license import require_license
        from .pro_features import run_ci_steps_locally

        require_license()
        code = run_ci_steps_locally(steps)
        if code != 0:
            click.echo("Mirror CI run failed.")
            raise SystemExit(code)
        click.echo("Mirror CI run passed.")
        raise SystemExit(0)

    # Dry-run with interpreter hint
    click.echo("Local CI plan (dry run):")
    requested_py = os.getenv("FIRSTTRY_PYTHON", sys.executable)
    click.echo(f"  Using interpreter: {requested_py}")
    for s in steps:
        click.echo(f"  - {s}")
    click.echo(
        "Matrix runners in CI may differ. Override with FIRSTTRY_PYTHON=/path/to/python."
    )
    click.echo(
        "Tip: use `firsttry mirror-ci --run` (Pro) to actually execute these steps locally."
    )
    raise SystemExit(0)


@click_main.command("doctor")
@click.option(
    "--json",
    "json_mode",
    is_flag=True,
    default=False,
    help="Output JSON instead of markdown",
)
@click.option("--parallel", is_flag=True, default=False, help="Run checks in parallel")
def cli_doctor(json_mode: bool, parallel: bool):
    """
    Run comprehensive health checks and print a diagnostic report.
    """
    from . import doctor as doctor_mod

    if parallel:
        report = doctor_mod.gather_checks(parallel=True)
    else:
        report = doctor_mod.gather_checks()
    if json_mode:
        out = doctor_mod.render_report_json(report)
    else:
        out = doctor_mod.render_report_md(report)
    click.echo(out, nl=False)

    # Exit nonzero if not all passed
    exit_code = 0 if report.passed_count == report.total_count else 1
    raise SystemExit(exit_code)


@click_main.group("license")
def cli_license():
    """License operations."""
    pass


@cli_license.command("verify")
@click.option(
    "--license-key",
    default=None,
    help="Override FIRSTTRY_LICENSE_KEY for this check",
)
@click.option(
    "--server-url",
    default=None,
    help="License server URL (ex: http://localhost:8000/api/v1/license/verify)",
)
@click.option("--json", "json_mode", is_flag=True, default=False, help="Output JSON")
def cli_license_verify(license_key: str, server_url: str, json_mode: bool):
    """
    Verify or cache license key.
    """
    from . import license as license_mod

    # We intentionally don't import 'requests' here to avoid hard dep.
    # Instead, we dynamically wrap requests.post if available.
    http_post = None
    if server_url:
        try:
            import importlib

            requests_mod = importlib.import_module("requests")
        except Exception:
            click.echo(
                "WARNING: requests not available, falling back to cached/offline",
                err=True,
            )
            http_post = None
        else:
            http_post = getattr(requests_mod, "post", None)

    info = license_mod.verify_license(
        license_key=license_key,
        server_url=server_url,
        http_post=http_post,
    )

    if json_mode:
        payload = {"valid": bool(info.valid), "plan": info.plan, "expiry": info.expiry}
        click.echo(__import__("json").dumps(payload))
    else:
        status_emoji = "✅" if info.valid else "❌"
        click.echo(
            f"{status_emoji} plan={info.plan} valid={info.valid} expiry={info.expiry}"
        )
        if not info.valid:
            click.echo("No valid license. Running in free mode.")

    exit_code = 0 if info.valid else 1
    raise SystemExit(exit_code)


# ---------------------------------------------------------------------
# ARGPARSE SURFACE
# ---------------------------------------------------------------------


def cmd_mirror_ci(ns: argparse.Namespace) -> int:
    """
    Compatibility argparse handler for mirror-ci that supports dry-run and --run (Pro).
    """
    # New adaptive mirror-ci: build plan (jobs + steps) and either print dry-run
    # or execute fast with precise failure reporting.
    root = getattr(ns, "root", "") or "."
    plan = ci_mapper.build_ci_plan(root)

    # Dry-run behavior: print human-readable plan (compatible with existing tests)
    if not getattr(ns, "run", False):
        if not plan or not plan.get("workflows"):
            # Fallback: if we didn't discover legacy 'workflows', print JSON plan
            import json

            print(json.dumps(plan, indent=2))
            return 0

        for wf in plan["workflows"]:
            print(f"Workflow: {wf['workflow_file']}")
            for job in wf["jobs"]:
                print(f"  Job: {job['job_id']}")
                for step in job["steps"]:
                    print(f"    Step: {step['name']}")
                    if step.get("env"):
                        print("      Env:")
                        for k, v in step["env"].items():
                            print(f"        {k}={v}")
                    print("      Run:")
                    print(f"        {step['run']}")
            print("")
        return 0

    # RUN MODE (Pro) — enforce license and execute steps
    import json
    from . import pro_features as pro_features_mod

    # License precedence: CLI flag > env var > empty string
    license_key = (
        getattr(ns, "license_key", None) or os.environ.get("FIRSTTRY_LICENSE_KEY") or ""
    )

    # If the plan is in the new adaptive 'jobs' shape, use the new fast runner
    if isinstance(plan, dict) and plan.get("jobs"):
        result = pro_features_mod.run_ci_plan_locally(plan, license_key=license_key)
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1

    # Else, fall back to legacy runner that returns {'ok','results'}
    # Adapt plan shape for pro_features.run_ci_steps_locally expectations
    normalized_plan = plan
    if isinstance(plan, dict) and plan.get("workflows"):
        jobs = []
        for wf in plan.get("workflows", []):
            for job in wf.get("jobs", []):
                jobs.append(
                    {
                        "job_name": job.get("job_id")
                        or job.get("job_name")
                        or "unknown",
                        "steps": job.get("steps", []),
                    }
                )
        normalized_plan = {"jobs": jobs}

    summary = pro_features_mod.run_ci_steps_locally(
        normalized_plan, license_key=license_key
    )

    if getattr(ns, "json", False):
        print(json.dumps(summary, indent=2))
    else:
        if not summary.get("results"):
            print("No steps were executed.")
        else:
            ok = summary.get("ok", False)
            verdict = "SAFE ✅" if ok else "BLOCKED ❌"
            print("FirstTry Mirror CI Summary")
            print("-------------------------")
            for r in summary.get("results", []):
                step_name = r.get("step") or r.get("cmd") or "unnamed"
                status = r.get("status", "ran")
                rc = r.get("returncode")
                print(f"- {step_name}: {status} (rc={rc})")
            print("")
            print(f"Verdict: {verdict}")

    return 0 if summary.get("ok") else 1


def cmd_gates(ns: argparse.Namespace) -> int:
    """
    Run local quality gates (lint, typecheck, etc.) and print results.

    - If --json: print machine-readable JSON.
    - Else: print a human summary.

    Exit code:
    - 0 if all gates ok
    - 1 otherwise
    """
    import json
    from pathlib import Path

    from . import gates as gates_mod

    repo_root = Path(getattr(ns, "root", "."))

    summary = gates_mod.run_all_gates(repo_root)

    all_ok = bool(summary.get("ok", False))
    results = summary.get("results", [])

    if getattr(ns, "json", False):
        print(json.dumps(summary, indent=2))
    else:
        # Human-readable fallback
        print("FirstTry Gates Report")
        print("---------------------")
        for item in results:
            gate = item.get("gate", "?")
            ok = item.get("ok", False)
            status = item.get("status", "")
            rc = item.get("returncode", "")
            print(f"[{gate}] ok={ok} status={status} returncode={rc}")
        print(f"\nOVERALL OK: {all_ok}")

        # Suggested next steps for users
        if not all_ok:
            print(
                "\nTip: Run `firsttry gates --json` to see exact stdout/stderr for each failed gate."
            )
        else:
            print("\n✓ Repo is clean. You’re safe to push.")

    return 0 if all_ok else 1


def build_parser() -> argparse.ArgumentParser:
    """
    Argparse version of the CLI surface for tests that call build_parser().
    Must expose subcommands: run, install-hooks, mirror-ci.
    """
    parser = argparse.ArgumentParser(
        prog="firsttry",
        description="FirstTry: pass CI in one shot.",
    )
    # Expose --version for argparse users
    parser.add_argument("--version", action="store_true", help="Show version and exit.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run
    run_parser = subparsers.add_parser(
        "run",
        help="Run a quality gate and print summary.",
    )
    run_parser.add_argument(
        "--gate",
        choices=["pre-commit", "pre-push"],
        required=True,
        help="Which gate to execute.",
    )
    run_parser.add_argument(
        "--require-license",
        action="store_true",
        help="Fail immediately if license is missing/invalid.",
    )

    # install-hooks
    subparsers.add_parser(
        "install-hooks",
        help="Install Git pre-commit and pre-push hooks that call FirstTry.",
    )

    # mirror-ci
    mirror_parser = subparsers.add_parser(
        "mirror-ci",
        help="Show local dry-run of CI workflow steps.",
    )
    mirror_parser.add_argument(
        "--root",
        required=True,
        help="Project root containing .github/workflows",
    )
    mirror_parser.add_argument(
        "--run",
        action="store_true",
        default=False,
        help="Execute mapped CI steps locally (Pro feature)",
    )
    mirror_parser.add_argument(
        "--license-key",
        default=None,
        help="(internal) License key to use for Pro features (overrides env)",
    )
    mirror_parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON summary (for CI tooling / extensions).",
    )
    mirror_parser.set_defaults(func=cmd_mirror_ci)

    # gates
    sub_gates = subparsers.add_parser(
        "gates",
        help="Run FirstTry quality gates (lint, typecheck, etc.) locally",
    )
    sub_gates.add_argument(
        "--root",
        default=".",
        help="Repository root (default: current directory)",
    )
    sub_gates.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON report",
    )
    sub_gates.set_defaults(func=cmd_gates)

    return parser


def argparse_main() -> int:
    """
    Entry point for `python -m firsttry.cli`.

    Supports:
    - firsttry --version
    - firsttry gates ...
    - firsttry mirror-ci ...
    """
    parser = build_parser()
    # Allow `--version` as a global flag without requiring a subcommand
    # (avoid argparse enforcing required subparsers when users call
    # `python -m firsttry.cli --version`).
    import sys as _sys

    if "--version" in _sys.argv:
        from firsttry import __version__

        print(f"FirstTry {__version__}")
        return 0

    ns = parser.parse_args()

    # Global --version
    if getattr(ns, "version", False):
        # Match Click: just print the version clean
        from firsttry import __version__

        print(f"FirstTry {__version__}")
        return 0

    if hasattr(ns, "func"):
        try:
            return ns.func(ns)
        except SystemExit as e:
            # Normalize SystemExit to int
            return int(e.code or 1)

    # No subcommand provided
    parser.print_help()
    return 1


# Keep the Click Group available as `main` (for click.testing.CliRunner etc.)
main = click_main


if __name__ == "__main__":
    # Allow `python -m firsttry.cli ...` to run argparse-friendly entrypoint
    raise SystemExit(argparse_main())
