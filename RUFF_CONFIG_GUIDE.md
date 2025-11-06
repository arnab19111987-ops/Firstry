# Dual Ruff Configuration Guide

## Overview

This repository uses a **dual Ruff configuration strategy** to balance developer velocity with code quality:

- **`.ruff.toml`** (baseline): Used for local development, CI/CD pipelines, and general use
- **`.ruff.pre-commit.toml`** (strict): Used exclusively by the pre-commit hook to enforce maximum code quality at commit time

## Configuration Files

### `.ruff.toml` — Baseline Configuration

**Purpose:** General-purpose configuration used everywhere except pre-commit.

**Key settings:**
- Line length: **100 characters**
- Rules: **E, F, I** (pycodestyle errors, Pyflakes, import order)
- Ignores: E203, E501 (Black-compatible, line-length delegated to line-length limit)
- Per-file ignores: Tests allow F821, E721, F841 (dynamic names, type comparisons)

**When used:**
```bash
ruff check .              # Local development
ruff check . --fix        # Auto-fix locally
pytest tests/             # During test runs
# CI/CD pipelines        # In GitHub Actions, etc.
```

### `.ruff.pre-commit.toml` — Strict Configuration

**Purpose:** Maximum strictness gate for pre-commit hook only.

**Key settings:**
- Extends: `.ruff.toml` (inherits baseline)
- Rules: **ALL** (every available rule, including preview rules)
- Fix enabled: **true** (auto-fixes violations)
- Preview rules: **true** (enables experimental rules)

**When used:**
```bash
# Only used by pre-commit hook
git commit -m "my changes"  # Runs strict gate automatically
```

## Pre-commit Integration

### Configuration

The `.pre-commit-config.yaml` has been updated to use the strict config:

```yaml
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.6.9
  hooks:
    - id: ruff
      name: ruff (strict gate)
      args:
        - --config=.ruff.pre-commit.toml      # Use strict config
        - --exit-non-zero-on-fix             # Fail if fixes needed
    - id: ruff-format
      name: ruff-format (strict gate)
      args:
        - --config=.ruff.pre-commit.toml
```

### Behavior

When you commit:

1. **Strict hook runs** with all rules enabled
2. **Auto-fixes applied** to any found issues
3. **Hook fails** if fixes were needed (exit-non-zero-on-fix)
4. **You must review & re-commit** the fixed changes

This ensures clean commits while preserving developer autonomy locally.

## Usage Examples

### Local Development (Baseline)

```bash
# Check with baseline rules
ruff check src/

# Auto-fix baseline issues
ruff check src/ --fix

# Format code (non-linting)
ruff format src/
```

### Testing (Baseline)

```bash
# Tests use baseline config
pytest tests/
```

### Pre-commit (Strict)

```bash
# Install hooks
pre-commit install

# Run all hooks (includes strict ruff)
pre-commit run --all-files

# Run just ruff (strict gate)
pre-commit run ruff --all-files

# Commit normally (hook runs automatically)
git add .
git commit -m "my changes"

# If hook fails due to fixes needed:
# 1. Review the fixes
git diff --cached
# 2. Stage the fixes
git add .
# 3. Re-commit
git commit -m "my changes (ruff formatting)"
```

## Rule Coverage

### Baseline (E, F, I)

- **E**: pycodestyle errors (whitespace, indentation, etc.)
- **F**: Pyflakes (undefined names, unused imports, etc.)
- **I**: isort (import sorting and formatting)

Example issues caught:
```python
import os                    # E402: unused import (F)
x=1                          # E225: whitespace around operator (E)
from datetime import date   # I001: import not sorted (I)
```

### Strict (ALL, including preview)

Enables ALL rules from ruff, including preview/experimental rules:

- **D**: docstring rules (pydocstyle)
- **A**: shadowed builtins (flake8-builtins)
- **C**: code complexity (McCabe, etc.)
- **T**: debug print statements (flake8-print)
- **RUF**: ruff-specific rules
- ...and 50+ more rule families

Example issues caught:
```python
def foo(input):               # A002: argument shadows builtin (A)
    """no docstring"""        # D100: missing module docstring (D)
    print(x)                  # T201: print found (T)
```

## Troubleshooting

### Pre-commit hook fails with "ruff failed"

Check your TOML syntax:
```bash
ruff check . --config=.ruff.pre-commit.toml
```

### Hook auto-fixes but I don't want them

This is intentional! The strict hook enforces a quality standard. Review the fixes:
```bash
git diff --cached
```

If they're acceptable, commit again.

### How to add ignores to strict config

Edit `.ruff.pre-commit.toml`:

```toml
[lint]
select = ["ALL"]
preview = true
ignore = ["D203", "D212"]  # Example: conflicting pydocstyle rules
```

Then reinstall:
```bash
pre-commit install
```

### How to exclude files from strict config

Edit `.ruff.pre-commit.toml`:

```toml
extend-exclude = [
  "tools/experimental.py",
  "scripts/old_migration.py",
]
```

### Verify configuration is correct

```bash
# Show baseline config
ruff show-settings --config=.ruff.toml

# Show strict config
ruff show-settings --config=.ruff.pre-commit.toml
```

## FAQ

**Q: Why two configs?**  
A: To allow fast, comfortable local development while maintaining high standards at commit time. Developers can run baseline checks locally without friction, then the strict gate ensures code quality.

**Q: Can I disable the pre-commit hook?**  
A: Temporarily:
```bash
git commit --no-verify  # Bypass hooks (not recommended!)
```

Permanently (not recommended):
```bash
pre-commit uninstall
```

**Q: Why does `--exit-non-zero-on-fix` cause issues?**  
A: This is intentional! It forces you to review auto-fixes before committing. This prevents surprises and ensures you understand what changed.

**Q: Can I change the baseline config?**  
A: Yes, edit `.ruff.toml` directly. Pre-commit will inherit changes via `extend = ".ruff.toml"`.

## Next Steps

1. ✅ **Dual config created:** `.ruff.toml` and `.ruff.pre-commit.toml`
2. ✅ **Pre-commit updated:** Points to `.ruff.pre-commit.toml` with `--exit-non-zero-on-fix`
3. ✅ **Hooks reinstalled:** `pre-commit install` completed
4. **Integrate into CI/CD:** Add baseline check to GitHub Actions
5. **Document in team guidelines:** Reference this guide in CONTRIBUTING.md

## References

- [Ruff Configuration Guide](https://docs.astral.sh/ruff/configuration/)
- [Pre-commit Documentation](https://pre-commit.com/)
- [Ruff Rules Reference](https://docs.astral.sh/ruff/rules/)
