# src/firsttry/cli_stable.py
from __future__ import annotations

from .cli import build_parser as _build_parser
from .cli import main as _main


def build_parser() -> object:
    return _build_parser()


def main(argv: list[str] | None = None) -> int:
    return _main(argv)
