from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from typing import Any

from .bandit import BanditRunner
from .base import CheckRunner
from .base import RunResult
from .mypy import MypyRunner
from .npm_lint import NpmLintRunner
from .npm_test import NpmTestRunner
from .pytest import PytestRunner
from .ruff import RuffRunner


class RegisteredRunner(CheckRunner):
    """Proxy that exposes the canonical synchronous CheckRunner.run signature.

    If the wrapped runner is a legacy BaseRunner (async idx/ctx/item), this
    proxy will adapt the canonical (repo_root, files, timeout_s) call into an
    appropriate ctx/item and run the legacy async runner via asyncio.run.
    Otherwise it forwards the call to the inner runner directly.
    """

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        # prefer to preserve a check_id if present
        self.check_id = getattr(inner, "check_id", getattr(inner, "tool", "unknown"))

    def prereq_check(self) -> str | None:
        return getattr(self.inner, "prereq_check", lambda: None)()

    def build_cache_key(self, repo_root: Path, targets: list[str], flags: list[str]) -> str:
        fn = getattr(self.inner, "build_cache_key", None)
        if fn:
            return fn(repo_root, targets, flags)
        return "ft-v1-unknown-0"

    def run(
        self, repo_root: Path, files: list[str] | None = None, *, timeout_s: int | None = None
    ) -> RunResult:
        # If inner.run is an async legacy runner (coroutine function expecting idx, ctx, item), adapt.
        inner_run = getattr(self.inner, "run")
        if inspect.iscoroutinefunction(inner_run):
            # build ctx and item from canonical params
            ctx: dict[str, Any] = {"repo_root": str(repo_root)}
            item: dict[str, Any] = {
                "tool": getattr(self.inner, "tool", getattr(self.inner, "check_id", "unknown")),
                "name": getattr(self.inner, "tool", None),
            }
            # run the async inner.run synchronously
            return asyncio.run(inner_run(0, ctx, item))
        # Otherwise assume it respects the canonical signature
        return inner_run(repo_root, files, timeout_s=timeout_s)


def default_registry() -> dict[str, CheckRunner]:
    return {
        "ruff": RegisteredRunner(RuffRunner()),
        "mypy": RegisteredRunner(MypyRunner()),
        "pytest": RegisteredRunner(PytestRunner()),
        "bandit": RegisteredRunner(BanditRunner()),
        "npm-lint": RegisteredRunner(NpmLintRunner()),
        "npm-test": RegisteredRunner(NpmTestRunner()),
    }
