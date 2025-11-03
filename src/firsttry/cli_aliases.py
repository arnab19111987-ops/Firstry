# src/firsttry/cli_aliases.py
"""
Lightweight alias entrypoint for FirstTry.

We only expose aliases for flows that are expected to be
FASTER than running the underlying tool directly.

Usage:
    ft lite         # main dev loop
    ft strict       # before push
    ft pro          # paid / CI-like
    ft doctor       # troubleshoot env
    ft setup        # install hooks
    ft dash         # show last run (dashboard view)
    ft lock         # show locked/tiered checks

    # tool-focused (fast paths)
    ft ruff         # run python lint via FirstTry
    ft mypy         # run types via FirstTry
    ft pytest       # run pytest via FirstTry (can be changed-only)
    ft js-test      # run npm/yarn/pnpm test via FirstTry smart_npm
"""

from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path


def _run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd)
    return proc.returncode


def main() -> None:
    args = sys.argv[1:]
    if not args:
        _print_help()
        raise SystemExit(1)

    sub = args[0]
    extra = args[1:]

    py = sys.executable
    base = [py, "-m", "firsttry"]

    # make sure we always have a place to write reports
    report_dir = Path(".firsttry")
    report_dir.mkdir(parents=True, exist_ok=True)
    default_report = str(report_dir / "report.json")

    # 1) core, tier-aware fast flows
    if sub in ("lite", "fast"):
        # main dev loop
        cmd = base + [
            "run",
            "fast",
            "--tier",
            "free-lite",
            "--profile",
            "fast",
            "--report-json",
            default_report,
            "--report-schema",
            "2",
        ] + extra
        raise SystemExit(_run(cmd))

    if sub in ("strict", "free-strict"):
        # before push, still free tier
        cmd = base + [
            "run",
            "strict",
            "--tier",
            "free-strict",
            "--report-json",
            default_report,
            "--report-schema",
            "2",
        ] + extra
        raise SystemExit(_run(cmd))

    if sub == "pro":
        # paid / CI-ish run
        cmd = base + [
            "run",
            "fast",
            "--tier",
            "pro",
            "--report-json",
            default_report,
        ] + extra
        raise SystemExit(_run(cmd))

    # 2) maintenance / visibility
    if sub == "doctor":
        cmd = base + ["doctor"] + extra
        raise SystemExit(_run(cmd))

    if sub == "doctor-checks":
        cmd = base + [
            "doctor",
            "--check",
            "report-json",
            "--check",
            "telemetry",
        ] + extra
        raise SystemExit(_run(cmd))

    if sub == "setup":
        cmd = base + ["setup", "--install-hooks"] + extra
        raise SystemExit(_run(cmd))

    if sub in ("dash", "dashboard"):
        cmd = base + [
            "inspect",
            "dashboard",
            "--json",
            default_report,
        ] + extra
        raise SystemExit(_run(cmd))

    if sub == "lock":
        cmd = base + [
            "inspect",
            "report",
            "--json",
            default_report,
            "--filter",
            "locked=true",
        ] + extra
        raise SystemExit(_run(cmd))

    # 3) tool-focused fast paths
    #
    # NOTE: FirstTry doesn't currently have an --only flag.
    # These aliases use the single-tool optimization by running
    # at free-lite tier where only ruff is allowed, or by
    # relying on the orchestrator to skip unavailable tools.
    #
    # For now, we'll just use tier filtering. In the future,
    # you can add --only flag support.
    #
    if sub == "ruff":
        cmd = base + [
            "run",
            "fast",
            "--tier",
            "free-lite",
            "--report-json",
            default_report,
        ] + extra
        raise SystemExit(_run(cmd))

    if sub == "mypy":
        # mypy requires higher tier, so use free-strict
        cmd = base + [
            "run",
            "fast",
            "--tier",
            "free-strict",
            "--report-json",
            default_report,
        ] + extra
        raise SystemExit(_run(cmd))

    if sub == "pytest":
        # pytest requires higher tier
        cmd = base + [
            "run",
            "fast",
            "--tier",
            "free-strict",
            "--report-json",
            default_report,
        ] + extra
        raise SystemExit(_run(cmd))

    if sub in ("js-test", "npm-test", "node-test"):
        # call FirstTry's smart_npm path
        cmd = base + [
            "run",
            "fast",
            "--tier",
            "free-strict",
            "--report-json",
            default_report,
        ] + extra
        raise SystemExit(_run(cmd))

    # unknown
    _print_help()
    raise SystemExit(1)


def _print_help() -> None:
    prog = os.path.basename(sys.argv[0]) or "ft"
    print(
        f"""Usage: {prog} <command> [options]

Core fast flows:
  {prog} lite
      -> python -m firsttry run fast --tier free-lite --profile fast --report-json .firsttry/report.json
  {prog} strict
      -> python -m firsttry run strict --tier free-strict --report-json .firsttry/report.json
  {prog} pro
      -> python -m firsttry run fast --tier pro --report-json .firsttry/report.json

Maintenance / visibility:
  {prog} doctor
      -> python -m firsttry doctor
  {prog} doctor-checks
      -> python -m firsttry doctor --check report-json --check telemetry
  {prog} setup
      -> python -m firsttry setup --install-hooks
  {prog} dash
      -> python -m firsttry inspect dashboard --json .firsttry/report.json
  {prog} lock
      -> python -m firsttry inspect report --json .firsttry/report.json --filter locked=true

Tool-focused (faster than manual in FT):
  {prog} ruff
      -> python -m firsttry run fast --tier free-lite --report-json .firsttry/report.json
  {prog} mypy
      -> python -m firsttry run fast --tier free-strict --report-json .firsttry/report.json
  {prog} pytest
      -> python -m firsttry run fast --tier free-strict --report-json .firsttry/report.json
  {prog} js-test
      -> python -m firsttry run fast --tier free-strict --report-json .firsttry/report.json

Extra flags still work, e.g.:
  {prog} lite --show-report
  {prog} strict --send-telemetry
  {prog} pytest --changed-only
"""
    )


if __name__ == "__main__":
    main()
