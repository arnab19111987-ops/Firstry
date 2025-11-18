from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

try:
    import typer
except Exception:  # pragma: no cover - optional runtime
    typer = None

# Repo root detection: allow env override for tests/CI
REPO_ROOT = Path(os.getenv("FIRSTTRY_REPO_ROOT", Path.cwd()))


@dataclass
class CmdResult:
    cmd: List[str]
    returncode: int


def run_cmd(
    args: Iterable[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[dict] = None,
    echo: bool = True,
) -> CmdResult:
    cmd_list = list(args)
    if echo:
        print(f"\n[firsttry] $ {' '.join(cmd_list)}", flush=True)

    cp = subprocess.run(
        cmd_list,
        cwd=str(cwd or REPO_ROOT),
        env=env,
        text=True,
    )

    return CmdResult(cmd=cmd_list, returncode=cp.returncode)


# ---------------------- Lint wrapper ----------------------
lint_app = typer.Typer(help="Lint wrapper commands") if typer else None


if lint_app is not None:
    @lint_app.callback(invoke_without_command=True)
    def lint_root(
        fast: bool = typer.Option(False, "--fast", help="Run fast lint (ruff only)."),
        full: bool = typer.Option(False, "--full", help="Run full lint (ruff + black --check + isort --check-only)."),
    ) -> None:
        if not fast and not full:
            fast = True

        results: List[CmdResult] = []

        if fast:
            results.append(run_cmd(["ruff", "."]))

        if full:
            results.append(run_cmd(["ruff", "."]))
            results.append(run_cmd(["black", "--check", "."]))
            results.append(run_cmd(["isort", "--check-only", "."]))

        exit_code = 0
        for r in results:
            if r.returncode != 0:
                exit_code = r.returncode
                break

        raise typer.Exit(code=exit_code)


# ---------------------- Pytest wrapper ----------------------
pytest_app = typer.Typer(help="Pytest wrapper commands") if typer else None


if pytest_app is not None:
    @pytest_app.callback(invoke_without_command=True)
    def pytest_root(
        fast: bool = typer.Option(False, "--fast", help="Run a fast subset of tests (no slow/e2e, stops on first failure)."),
        full: bool = typer.Option(False, "--full", help="Run the full test suite."),
        extra_args: Optional[str] = typer.Option(None, "--extra-args", help="Additional arguments to pass to pytest."),
    ) -> None:
        if fast and full:
            typer.echo("Cannot use --fast and --full together.", err=True)
            raise typer.Exit(code=2)

        if not fast and not full:
            fast = True

        base_cmd: List[str] = ["pytest"]
        if extra_args:
            base_cmd.extend(extra_args.split())

        if fast:
            cmd = base_cmd + ["-q", "-k", "not slow and not e2e", "--maxfail=1"]
        else:
            cmd = base_cmd + ["-q"]

        result = run_cmd(cmd)
        raise typer.Exit(code=result.returncode)


# ---------------------- Typecheck wrapper ----------------------
typecheck_app = typer.Typer(help="Type-check wrapper commands") if typer else None


if typecheck_app is not None:
    @typecheck_app.callback(invoke_without_command=True)
    def typecheck_root(
        path: str = typer.Option("src/firsttry", "--path", help="Path to type-check (default: src/firsttry)."),
        include_tests: bool = typer.Option(False, "--include-tests", help="Also type-check tests/ directory."),
    ) -> None:
        targets: List[str] = [path]
        if include_tests:
            targets.append("tests")

        cmd = ["mypy"] + targets
        result = run_cmd(cmd)
        raise typer.Exit(code=result.returncode)


# ---------------------- SBOM wrapper ----------------------
sbom_app = typer.Typer(help="SBOM generation wrapper commands") if typer else None


if sbom_app is not None:
    @sbom_app.callback(invoke_without_command=True)
    def sbom_root(
        python: bool = typer.Option(True, "--python/--no-python", help="Generate Python SBOM."),
        node: bool = typer.Option(False, "--node/--no-node", help="Generate Node.js SBOM."),
        output_dir: str = typer.Option("artifacts/sbom", "--output-dir", help="Directory to write SBOM files into."),
    ) -> None:
        out_dir = REPO_ROOT / output_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        results: List[CmdResult] = []

        if python:
            results.append(
                run_cmd([
                    "cyclonedx-bom",
                    "--environment",
                    "python",
                    "--format",
                    "json",
                    "--output",
                    str(out_dir / "sbom-python.json"),
                ])
            )

        if node:
            results.append(
                run_cmd([
                    "cyclonedx-bom",
                    "--environment",
                    "node",
                    "--format",
                    "json",
                    "--output",
                    str(out_dir / "sbom-node.json"),
                ])
            )

        exit_code = 0
        for r in results:
            if r.returncode != 0:
                exit_code = r.returncode
                break

        raise typer.Exit(code=exit_code)


# ---------------------- Security audit wrapper ----------------------
security_app = typer.Typer(help="Security audit wrapper commands") if typer else None


if security_app is not None:
    @security_app.callback(invoke_without_command=True)
    def security_root(
        bandit_target: str = typer.Option("src/firsttry", "--bandit-target", help="Path for Bandit to scan."),
        safety_requirements: str = typer.Option("requirements.txt", "--safety-requirements", help="Requirements file to scan with safety."),
    ) -> None:
        results: List[CmdResult] = []

        results.append(
            run_cmd([
                "bandit",
                "-r",
                bandit_target,
                "-f",
                "json",
                "-o",
                "artifacts/bandit-report.json",
            ])
        )

        req_path = REPO_ROOT / safety_requirements
        if req_path.exists():
            results.append(
                run_cmd([
                    "safety",
                    "check",
                    "--file",
                    str(req_path),
                    "--full-report",
                ])
            )
        else:
            print(f"[firsttry] NOTE: requirements file '{req_path}' not found; skipping safety check.")

        exit_code = 0
        for r in results:
            if r.returncode != 0:
                exit_code = r.returncode
                break

        raise typer.Exit(code=exit_code)


def register_cli_wrappers(app: "typer.Typer") -> None:  # type: ignore[name-defined]
    """Register available wrapper subcommands onto a parent Typer app.

    This is deliberately non-fatal: it only registers wrappers that were
    successfully created (Typer present). Callers can safely ignore return
    or catch exceptions.
    """
    if lint_app is not None:
        app.add_typer(lint_app, name="lint")
    if pytest_app is not None:
        app.add_typer(pytest_app, name="pytest")
    if typecheck_app is not None:
        app.add_typer(typecheck_app, name="typecheck")
    if sbom_app is not None:
        app.add_typer(sbom_app, name="sbom")
    if security_app is not None:
        app.add_typer(security_app, name="security-audit")
