from __future__ import annotations
from dataclasses import dataclass
from time import perf_counter
import subprocess
from typing import Iterable, Sequence
from pathlib import Path
import xml.etree.ElementTree as ET

# Optional compatibility alias; keep after other imports so linters don't
# complain about non-top-level imports. Tests should patch `subprocess.run`
# directly, but exposing this alias doesn't hurt external users that import
# `firsttry.runners.run`.
run = subprocess.run


@dataclass(frozen=True)
class StepResult:
    name: str
    ok: bool
    duration_s: float
    stdout: str
    stderr: str
    cmd: tuple[str, ...]


def _exec(name: str, args: Sequence[str], cwd: Path | None = None) -> StepResult:
    t0 = perf_counter()
    # Debug: write the current 'run' callable to a debug log to help track
    # test-order related monkeypatching issues. This is temporary and will be
    # removed once the root cause is confirmed.
    # Call subprocess.run dynamically so tests can monkeypatch
    # `subprocess.run` at runtime and have `_exec` pick up the stub even if
    # this module bound an alias at import time.
    proc = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(cwd) if cwd else None,
    )
    dt = perf_counter() - t0
    return StepResult(
        name=name,
        ok=(proc.returncode == 0),
        duration_s=dt,
        stdout=proc.stdout,
        stderr=proc.stderr,
        cmd=tuple(args),
    )


def run_ruff(paths: Iterable[str] = (".",)) -> StepResult:
    return _exec("ruff", ["ruff", "check", *paths])


def run_black_check(paths: Iterable[str] = (".",)) -> StepResult:
    return _exec("black", ["black", "--check", *paths])


def run_mypy(paths: Iterable[str]) -> StepResult:
    return _exec("mypy", ["mypy", *paths])


def run_pytest_kexpr(
    kexpr: str | None, base_args: Sequence[str] = ("-q",)
) -> StepResult:
    args = ["pytest", *base_args]
    if kexpr:
        args += ["-k", kexpr]
    return _exec("pytest", args)


def run_coverage_xml(
    kexpr: str | None, base_args: Sequence[str] = ("-q",)
) -> StepResult:
    args = ["coverage", "run", "-m", "pytest", *base_args]
    if kexpr:
        args += ["-k", kexpr]
    res = _exec("coverage_run", args)
    if not res.ok:
        return res
    # create XML for gate to parse
    xml_res = _exec("coverage_xml", ["coverage", "xml", "-o", "coverage.xml"])
    return xml_res


def parse_cobertura_line_rate(xml_path: Path = Path("coverage.xml")) -> float | None:
    if not xml_path.exists():
        return None
    root = ET.parse(str(xml_path)).getroot()
    # coverage.py uses Cobertura; root tag is 'coverage' with line-rate attr
    rate = root.attrib.get("line-rate")
    return float(rate) * 100 if rate is not None else None


def coverage_gate(threshold: int) -> StepResult:
    rate = parse_cobertura_line_rate()
    ok = (rate is not None) and (rate >= threshold)
    stdout = (
        f"coverage: {rate:.2f}% (threshold {threshold}%)"
        if rate is not None
        else "no coverage.xml"
    )
    return StepResult(
        "coverage_gate", ok, 0.0, stdout, "", ("coverage_gate", str(threshold))
    )
