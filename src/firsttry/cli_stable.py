# src/firsttry/cli_stable.py
from __future__ import annotations

from typing import List, Optional

from .cli import build_parser as _build_parser
from .cli import main as _main


def build_parser() -> object:
    return _build_parser()


def main(argv: Optional[List[str]] = None) -> int:
    return _main(argv)
