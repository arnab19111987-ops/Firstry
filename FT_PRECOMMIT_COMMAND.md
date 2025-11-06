# `ft pre-commit` Command Setup

## Overview

Added a new `ft pre-commit` alias command to make it easy to run pre-commit hooks with the strict Ruff configuration gate.

## Command Details

### What it does:
```bash
ft pre-commit
```

Equivalent to:
```bash
pre-commit run --all-files
```

This runs all pre-commit hooks configured in `.pre-commit-config.yaml` with the strict Ruff config (`.ruff.pre-commit.toml`), which enables ALL rules and auto-fixes.

### Usage Examples:

```bash
# Run all pre-commit hooks on all files
ft pre-commit

# Run just the Ruff hook
ft pre-commit ruff

# Run with specific options
ft pre-commit --verbose
ft pre-commit --show-diff-on-failure
```

## How it fits into the workflow

### Normal Git commit:
```bash
git add .
git commit -m "my changes"
# Pre-commit hook runs automatically (uses strict Ruff gate)
```

### Manual pre-commit check before committing:
```bash
ft pre-commit
# Reviews all hooks; ruff-format may auto-fix files
# Review the fixes and re-add if needed
```

### Quick development loop:
```bash
ft lite              # Run baseline checks (fast)
ft pre-commit        # Run strict gate (before commit)
git commit -m "..."  # Commit (if no fixes needed)
```

## Integration with Dual Ruff Config

The `ft pre-commit` command leverages the dual Ruff configuration:

- **Baseline** (`.ruff.toml`): Used by `ft lite`, `ft strict`, `ft ruff`, etc.
- **Strict** (`.ruff.pre-commit.toml`): Used by `ft pre-commit` and the Git pre-commit hook

This ensures:
- Fast local development with baseline checks
- Strong quality gate at commit time with ALL rules
- Auto-fixes are applied and must be reviewed

## Files Modified

- `src/firsttry/cli_aliases.py` — Added pre-commit command and updated help text

## Command Reference

```bash
ft lite              # Baseline fast checks (E, F, I rules)
ft strict            # Baseline strict checks (ruff + mypy + pytest)
ft pre-commit        # Strict gate (ALL rules, auto-fix enabled)
ft setup             # Install pre-commit hooks
```

All three work together:
1. `ft lite` — Fast feedback during development
2. `ft pre-commit` — Manual pre-commit check before committing
3. Git hook — Automatic enforcement at commit time
