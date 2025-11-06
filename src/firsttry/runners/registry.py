from __future__ import annotations

from .bandit import BanditRunner
from .base import CheckRunner
from .mypy import MypyRunner
from .npm_lint import NpmLintRunner
from .npm_test import NpmTestRunner
from .pytest import PytestRunner
from .ruff import RuffRunner


def default_registry() -> dict[str, CheckRunner]:
    return {
        "ruff": RuffRunner(),
        "mypy": MypyRunner(),
        "pytest": PytestRunner(),
        "bandit": BanditRunner(),
        "npm-lint": NpmLintRunner(),
        "npm-test": NpmTestRunner(),
    }
