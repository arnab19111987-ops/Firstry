from __future__ import annotations
from typing import Dict
from .base import CheckRunner
from .ruff import RuffRunner
from .mypy import MypyRunner
from .pytest import PytestRunner


def default_registry() -> Dict[str, CheckRunner]:
    return {
        "ruff": RuffRunner(),
        "mypy": MypyRunner(),
        "pytest": PytestRunner(),
        # add: bandit, duplication, drift, coverage...
    }
