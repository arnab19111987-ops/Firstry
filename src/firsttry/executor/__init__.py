"""Executor package for FirstTry DAG execution."""

# Public, circular-safe re-export
from ..compat_shims import execute_plan  # noqa: F401

__all__ = ["execute_plan"]
