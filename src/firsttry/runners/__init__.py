"""Lightweight test-friendly runners and small runtime shim.

Provides a simple RunResult type and _exec helper that calls subprocess.run
at runtime (so tests can monkeypatch subprocess.run dynamically). The
functions expose predictable signatures used by the test-suite.
"""

import os
import subprocess
import time
import types
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

__all__ = [
    "RunResult",
    "_exec",
    "run_ruff",
    "run_black_check",
    "run_mypy",
    "run_pytest_kexpr",
    "parse_cobertura_line_rate",
    "run_coverage_xml",
    "coverage_gate",
    "RUNNERS",
]


class RunResult(types.SimpleNamespace):
    """Small dataclass-like container tests expect (attributes used in asserts).

    Attributes: ok, name, duration_s, stdout, stderr, cmd
    """

    @property
    def status(self) -> str:
        return "ok" if getattr(self, "ok", False) else "error"


def _exec(
    name: str, args: Sequence[str], *, cwd: Path | str | None = None, timeout: float | None = None
) -> RunResult:
    t0 = time.time()
    try:
        # Call subprocess.run at runtime so tests can monkeypatch subprocess.run
        run_kwargs: dict = {"stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "text": True}
        if cwd is not None:
            run_kwargs["cwd"] = cwd
        if timeout is not None:
            run_kwargs["timeout"] = timeout
        p = subprocess.run(list(args), **run_kwargs)
        dur = time.time() - t0
        ok = p.returncode == 0
        status = "ok" if ok else "error"
        return RunResult(
            ok=ok,
            status=status,
            name=name,
            duration_s=dur,
            stdout=p.stdout or "",
            stderr=p.stderr or "",
            cmd=tuple(args),
            meta={},
        )
    except subprocess.TimeoutExpired as e:
        dur = time.time() - t0
        return RunResult(
            ok=False,
            status="timeout",
            name=name,
            duration_s=dur,
            stdout=getattr(e, "stdout", "") or "",
            stderr=str(e),
            cmd=tuple(args),
            meta={},
        )


def run_command(cmd: list[str] | str, cwd: str | Path | None = None, timeout: Optional[int] = None):
    """Compatibility wrapper used by higher-level runners and tests.

    Returns an object with a `returncode` attribute and optional stdout/stderr.
    """
    # Normalize to argument list
    if isinstance(cmd, str):
        cmd_list = cmd.split()
    else:
        cmd_list = list(cmd)

    name = cmd_list[0] if cmd_list else "cmd"
    rr = _exec(name, cmd_list, cwd=cwd, timeout=timeout)

    # Normalize to a CompletedProcess-like simple namespace so callers
    # that expect `.returncode` keep working.
    return types.SimpleNamespace(
        returncode=(0 if getattr(rr, "ok", False) else 1),
        stdout=getattr(rr, "stdout", ""),
        stderr=getattr(rr, "stderr", ""),
    )


def run_ruff(
    files: Iterable[str], *, cwd: Path | None = None, timeout: Optional[int] = None
) -> RunResult:
    args = ["ruff", "check", *files]
    # Prefer the external run_command wrapper so tests can monkeypatch it.
    completed = run_command(args, cwd=cwd, timeout=timeout)
    ok = getattr(completed, "returncode", 1) == 0
    return RunResult(
        ok=ok,
        name="ruff",
        duration_s=0.0,
        stdout=getattr(completed, "stdout", "") or "",
        stderr=getattr(completed, "stderr", "") or "",
        cmd=tuple(args),
        meta={},
    )


def run_black_check(
    targets: Iterable[str], *, cwd: Path | None = None, timeout: Optional[int] = None
) -> RunResult:
    args = ["black", "--check", *targets]
    return _exec("black", args, cwd=cwd, timeout=timeout)


def run_mypy(
    files: Iterable[str], *, cwd: Path | None = None, timeout: Optional[int] = None
) -> RunResult:
    args = ["mypy", *files]
    completed = run_command(args, cwd=cwd, timeout=timeout)
    ok = getattr(completed, "returncode", 1) == 0
    return RunResult(
        ok=ok,
        name="mypy",
        duration_s=0.0,
        stdout=getattr(completed, "stdout", "") or "",
        stderr=getattr(completed, "stderr", "") or "",
        cmd=tuple(args),
        meta={},
    )


def run_pytest_kexpr(
    kexpr: str,
    *,
    base_args: Sequence[str] = (),
    cwd: Path | None = None,
    timeout: Optional[int] = None,
) -> RunResult:
    args = ["pytest", *base_args, "-k", kexpr]
    completed = run_command(args, cwd=cwd, timeout=timeout)
    ok = getattr(completed, "returncode", 1) == 0
    return RunResult(
        ok=ok,
        name="pytest",
        duration_s=0.0,
        stdout=getattr(completed, "stdout", "") or "",
        stderr=getattr(completed, "stderr", "") or "",
        cmd=tuple(args),
        meta={},
    )


def run_pytest_files(
    files: Iterable[str],
    *,
    base_args: Sequence[str] = (),
    cwd: Path | None = None,
    timeout: Optional[int] = None,
) -> RunResult:
    args = ["pytest", *base_args, *files]
    completed = run_command(args, cwd=cwd, timeout=timeout)
    ok = getattr(completed, "returncode", 1) == 0
    return RunResult(
        ok=ok,
        name="pytest",
        duration_s=0.0,
        stdout=getattr(completed, "stdout", "") or "",
        stderr=getattr(completed, "stderr", "") or "",
        cmd=tuple(args),
        meta={},
    )


def parse_cobertura_line_rate(xml_text: str | None = None) -> float | None:
    """Return line-rate as a percent (0-100) or None on parse/missing.

    If xml_text is None, attempt to read ./coverage.xml.
    """
    try:
        if xml_text is None:
            p = Path("coverage.xml")
            if not p.exists():
                return None
            xml_text = p.read_text(encoding="utf-8", errors="ignore")
        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml_text)
        val = root.get("line-rate")
        return round(float(val) * 100.0, 2) if val is not None else None
    except Exception:
        return None


def run_coverage_xml(root: str | Path) -> RunResult:
    p = Path(root) / "coverage.xml"
    if not p.exists():
        return RunResult(
            ok=False,
            name="coverage",
            duration_s=0.0,
            stdout="coverage.xml missing",
            stderr="",
            cmd=(),
        )
    rate = parse_cobertura_line_rate(p.read_text(encoding="utf-8", errors="ignore"))
    if rate is None:
        return RunResult(
            ok=False, name="coverage", duration_s=0.0, stdout="no coverage.xml", stderr="", cmd=()
        )
    return RunResult(
        ok=(rate >= 0.0),
        name="coverage",
        duration_s=0.0,
        stdout=f"coverage xml parsed: {rate:.2f}%",
        stderr="",
        cmd=(),
    )


def coverage_gate(min_percent: int) -> RunResult:
    rate = parse_cobertura_line_rate()
    if rate is None:
        return RunResult(
            ok=False,
            name="coverage_gate",
            duration_s=0.0,
            stdout="no coverage.xml",
            stderr="",
            cmd=(),
        )
    ok = rate >= float(min_percent)
    msg = f"coverage gate {'PASS' if ok else 'FAIL'} ({rate:.2f}% >= {min_percent}%)"
    return RunResult(ok=ok, name="coverage_gate", duration_s=0.0, stdout=msg, stderr="", cmd=())


# Default RUNNERS mapping (kept minimal; tests often monkeypatch the orchestrator directly)
RUNNERS: dict[str, Any] = {}

if os.getenv("FIRSTTRY_USE_REAL_RUNNERS") in ("1", "true", "True"):
    try:
        from .real import (
            coverage_gate as _real_coverage_gate,
            run_black_check as _real_run_black_check,
            run_coverage_xml as _real_run_coverage_xml,
            run_mypy as _real_run_mypy,
            run_pytest_kexpr as _real_run_pytest_kexpr,
            run_ruff as _real_run_ruff,
        )

        run_ruff = _real_run_ruff
        run_black_check = _real_run_black_check
        run_mypy = _real_run_mypy
        run_pytest_kexpr = _real_run_pytest_kexpr
        run_coverage_xml = _real_run_coverage_xml
        coverage_gate = _real_coverage_gate
    except Exception:
        pass
