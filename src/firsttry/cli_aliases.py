import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, Sequence


def _run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd)
    return proc.returncode


@dataclass(frozen=True)
class AliasSpec:
    name: str
    args: Sequence[str]


# Single source of truth for all ft aliases
FT_ALIAS_MAP: Dict[str, AliasSpec] = {
    "pytest": AliasSpec(
        name="pytest",
        args=[
            "run",
            "fast",
            "--tier",
            "strict",
            "--report-json",
            ".firsttry/report.json",
        ],
    ),
    "strict": AliasSpec(
        name="strict",
        args=[
            "run",
            "strict",
            "--tier",
            "free-strict",
            "--report-json",
            ".firsttry/report.json",
            "--report-schema",
            "2",
        ],
    ),
    "lite": AliasSpec(
        name="lite",
        args=[
            "run",
            "fast",
            "--tier",
            "free-lite",
            "--profile",
            "fast",
            "--report-json",
            ".firsttry/report.json",
            "--report-schema",
            "2",
        ],
    ),
    "doctor-checks": AliasSpec(
        name="doctor-checks",
        args=[
            "doctor",
            "--check",
            "report-json",
            "--check",
            "telemetry",
        ],
    ),
    "dash": AliasSpec(
        name="dash",
        args=["inspect", "dashboard", "--json", ".firsttry/report.json"],
    ),
    "lock": AliasSpec(
        name="lock",
        args=[
            "inspect",
            "report",
            "--json",
            ".firsttry/report.json",
            "--filter",
            "locked=true",
        ],
    ),
    "setup": AliasSpec(
        name="setup",
        args=["setup", "--install-hooks"],
    ),
    "pro": AliasSpec(
        name="pro",
        args=["run", "fast", "--tier", "pro", "--report-json", ".firsttry/report.json"],
    ),
    # Add more aliases as needed
}


def dispatch_alias(alias: str, extra_args: Sequence[str]) -> int:
    py = sys.executable
    base = [py, "-m", "firsttry"]
    try:
        spec = FT_ALIAS_MAP[alias]
    except KeyError:
        _print_help()
        raise SystemExit(1)
    full_args = list(spec.args) + list(extra_args)
    cmd = base + full_args
    return _run(cmd)


def main() -> None:
    args = sys.argv[1:]
    if not args:
        _print_help()
        raise SystemExit(1)
    sub = args[0]
    extra = args[1:]
    # Use dispatch_alias for all FT_ALIAS_MAP aliases
    if sub in FT_ALIAS_MAP:
        raise SystemExit(dispatch_alias(sub, extra))

    if sub in ("js-test", "npm-test", "node-test"):
        # call FirstTry's smart_npm path
        base = [sys.executable, "-m", "firsttry"]
        default_report = ".firsttry/report.json"
        cmd = (
            base
            + [
                "run",
                "fast",
                "--tier",
                "free-strict",
                "--report-json",
                default_report,
            ]
            + extra
        )
        raise SystemExit(_run(cmd))

    # unknown
    _print_help()
    raise SystemExit(1)


def _print_help() -> None:
    prog = os.path.basename(sys.argv[0]) or "ft"
    print(f"Usage: {prog} <command> [options]\n")
    print("Core fast flows:")
    print(
        f"  {prog} lite -> python -m firsttry run fast --tier free-lite --profile fast --report-json .firsttry/report.json"
    )
    print(
        f"  {prog} strict -> python -m firsttry run strict --tier free-strict --report-json .firsttry/report.json"
    )
    print(
        f"  {prog} pro -> python -m firsttry run fast --tier pro --report-json .firsttry/report.json"
    )
    print("\nMaintenance / visibility:")
    print(f"  {prog} doctor -> python -m firsttry doctor")
    print(
        f"  {prog} doctor-checks -> python -m firsttry doctor --check report-json --check telemetry"
    )
    print(f"  {prog} setup -> python -m firsttry setup --install-hooks")
    print(
        f"  {prog} dash -> python -m firsttry inspect dashboard --json .firsttry/report.json"
    )
    print(
        f"  {prog} lock -> python -m firsttry inspect report --json .firsttry/report.json --filter locked=true"
    )


if __name__ == "__main__":
    main()
