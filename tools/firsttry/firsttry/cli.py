from __future__ import annotations
import sys
from typing import Optional
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .config import FirstTryConfig
from .changed import get_changed_files, filter_python
from .mapper import guess_test_kexpr
from .hooks import install_pre_commit_hook
from . import runners
from .license_cache import assert_license

console = Console()


@click.group(help="FirstTry CLI — mirror CI gates locally")
def main() -> None:
    pass


@main.command("run")
@click.option(
    "--gate",
    type=click.Choice(["pre-commit", "pre-push"], case_sensitive=False),
    required=True,
    help="Which gate to execute",
)
@click.option(
    "--require-license/--no-require-license",
    default=False,
    help="Validate license before running gate (uses weekly offline cache).",
)
def cmd_run(gate: str, require_license: bool) -> None:
    cfg = FirstTryConfig.load()
    if gate == "pre-commit":
        install_pre_commit_hook()
    if require_license:
        ok, feats, src = assert_license()
        if not ok:
            console.print("[red]License invalid or missing — aborting gate.[/red]")
            raise SystemExit(1)
        console.print(f"[green]License ok ({src})[/green] features={feats}")
    changed = filter_python(get_changed_files("HEAD"))
    kexpr: Optional[str] = guess_test_kexpr(changed) if changed else None

    results = []
    results.append(runners.run_ruff(("tools/firsttry",)))
    results.append(runners.run_black_check(("tools/firsttry",)))
    results.append(runners.run_mypy(("tools/firsttry",)))

    # fast targeted tests first
    results.append(runners.run_pytest_kexpr(kexpr, cfg.pytest_base_args))
    # then coverage (full or filtered the same k)
    cov_xml = runners.run_coverage_xml(kexpr, cfg.pytest_base_args)
    results.append(cov_xml)
    # gate
    results.append(runners.coverage_gate(cfg.coverage_threshold))

    _render_summary(results)
    ok = all(r.ok for r in results)
    sys.exit(0 if ok else 1)


def _render_summary(results) -> None:
    table = Table(title="FirstTry Gate Summary", show_lines=True)
    table.add_column("Step")
    table.add_column("OK")
    table.add_column("Dur (s)")
    table.add_column("Cmd")
    for r in results:
        table.add_row(
            r.name, "✅" if r.ok else "❌", f"{r.duration_s:.2f}", " ".join(r.cmd)
        )
    console.print(Panel(table, border_style="cyan"))
