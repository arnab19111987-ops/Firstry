# src/firsttry/reports/ui.py
from __future__ import annotations
import os
import sys
import time
from typing import Dict, Any, List

# try to use rich if present
try:
    from rich.console import Console
    from rich.progress import (
        Progress,
        SpinnerColumn,
        TextColumn,
        BarColumn,
        TimeElapsedColumn,
    )

    _HAS_RICH = True
    _console = Console()
except Exception:  # pragma: no cover
    _HAS_RICH = False
    _console = None  # type: ignore[assignment]


def _supports_color() -> bool:
    if _HAS_RICH:
        return True
    if not sys.stdout.isatty():
        return False
    return os.environ.get("TERM") not in (None, "dumb")


def c(text: str, color: str) -> str:
    """Minimal ANSI coloring fallback."""
    if not _supports_color():
        return text
    colors = {
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "bold": "\033[1m",
    }
    reset = "\033[0m"
    return f"{colors.get(color, '')}{text}{reset}"


def render_run_progress(checks: List[str]):
    """
    Show a short 'running checks' progress. Call this BEFORE you actually run
    or simulate running while orchestrator is doing work.
    """
    if _HAS_RICH:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=_console,
        ) as progress:
            task = progress.add_task("Running checks…", total=len(checks))
            for _ in checks:
                # we don't know actual duration, so simulate small steps
                time.sleep(0.05)
                progress.advance(task)
    else:
        # simple fallback
        sys.stdout.write("Running checks")
        sys.stdout.flush()
        for _ in checks:
            time.sleep(0.05)
            sys.stdout.write(".")
            sys.stdout.flush()
        sys.stdout.write("\n")


def interactive_menu(
    results: Dict[str, Any],
    allowed_checks: List[str],
    locked_msg: str,
    on_detail,
    on_locked,
):
    """
    Show a small interactive menu AFTER summary.
    """
    while True:
        print()
        print(c("What would you like to do next?", "bold"))
        print(c("  1) View detailed report (unlocked checks only)", "green"))
        print(c("  2) View locked / Pro checks", "yellow"))
        print(c("  3) How to upgrade", "cyan"))
        print(c("  4) Exit", "red"))
        choice = input(c("Select option [1-4]: ", "bold")).strip()

        if choice == "1":
            on_detail(results, allowed_checks)
        elif choice == "2":
            on_locked(results, allowed_checks, locked_msg)
        elif choice == "3":
            print()
            print(c("Upgrade to FirstTry Pro / Team to unlock:", "bold"))
            print("  • Security scanning (bandit)")
            print("  • Dependency audit (pip-audit)")
            print("  • CI-parity validation (match your GitHub/GitLab CI)")
            print("  • Coverage and secrets scanning (Team/Enterprise)")
            print()
            print("Run: " + c("firsttry upgrade", "green"))
        elif choice == "4":
            print(c("Bye 👋", "blue"))
            break
        else:
            print(c("Invalid option. Try again.", "red"))
