from __future__ import annotations
from typing import Dict
from .base import CheckRunner
from .ruff import RuffRunner
from .mypy import MypyRunner
from .pytest import PytestRunner
from .bandit import BanditRunner
from .npm_lint import NpmLintRunner
from .npm_test import NpmTestRunner


def default_registry() -> Dict[str, CheckRunner]:
    return {
        "ruff": RuffRunner(),
        "mypy": MypyRunner(),
        "pytest": PytestRunner(),
        "bandit": BanditRunner(),
        "npm-lint": NpmLintRunner(),
        "npm-test": NpmTestRunner(),
    }
