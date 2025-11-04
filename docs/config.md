Configuration precedence

firsttry looks for runtime configuration in this order (highest → lowest precedence):

- `firsttry.toml` (recommended single-source-of-truth for local/team config)
- `pyproject.toml` in `[tool.firsttry]` (fallback, mostly used for package metadata)

We recommend keeping Bandit and other runtime checks in `firsttry.toml` to avoid surprises.

Bandit config keys (canonical):

[tool.firsttry.checks.bandit]
- enabled: bool (true/false)
- blocking: bool (if true the run fails when findings >= fail_on)
- fail_on: string (one of "low", "medium", "high", "critical")
- jobs: integer (0 to auto-detect CPU count; >0 to parallelize shards)
- include: list of paths (e.g., ["src"] or [""] for repo-root layout)
- exclude: list of path patterns to skip
- extra_args: list of additional CLI args to pass to Bandit (e.g., ['-q'])

Note: `firsttry.toml` overrides `[tool.firsttry]` in `pyproject.toml`.
