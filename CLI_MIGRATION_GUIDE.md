# CLI Migration Guide: From `--gate` to Mode-Based System

## Overview

FirstTry has evolved from a flag-based CLI (`--gate`, `--require-license`) to a cleaner mode-based system. **The old flags still work** via a backward-compatibility shim, but they are deprecated.

## What Changed?

### Old CLI Design
```bash
# Individual gate flags for each check
firsttry run --gate ruff
firsttry run --gate strict
firsttry run --require-license
```

### New CLI Design
```bash
# Mode-based system with cleaner semantics
firsttry run fast                    # ruff only (free)
firsttry run strict                  # ruff + mypy + pytest (free)
firsttry run pro                     # pro features (requires license)
firsttry run --tier pro              # explicit tier control
```

## Migration Cheat Sheet

| Legacy Command | New Command | Tier | Checks |
|---|---|---|---|
| `--gate ruff` | `run fast` | free-lite | ruff only |
| `--gate pre-commit` | `run fast` | free-lite | ruff only |
| `--gate strict` | `run strict` | free-strict | ruff + mypy + pytest |
| `--gate ci` | `run ci` | free-strict | ruff + mypy + pytest |
| `--gate mypy` | `run strict` | free-strict | ruff + mypy + pytest |
| `--gate pytest` | `run strict` | free-strict | ruff + mypy + pytest |
| `--require-license` | `run --tier pro` | pro | full suite |
| `--gate strict --require-license` | `run strict --tier pro` | pro | full suite |

## Backward Compatibility

Old commands will continue to work but will print a deprecation notice:

```bash
$ firsttry run --gate pre-commit
[firsttry] DEPRECATED: --gate/--require-license are no longer supported.
           Use 'run <mode>' (fast|strict|pro|enterprise) or '--tier <tier>' instead.
           See: https://docs.firsttry.com/cli-migration
```

### How the Shim Works

The CLI automatically translates legacy flags:

```python
# Legacy input
firsttry run --gate pre-commit --require-license

# Automatically translated to
firsttry run fast --tier pro
```

Translation rules:
- `--gate pre-commit|precommit|ruff` → mode `fast`
- `--gate strict|ci|mypy|pytest` → mode `strict`
- `--gate <unknown>` → mode `fast` (safe default)
- `--require-license` → `--tier pro`

## Recommended Updates

### 1. Pre-Commit Hooks

**Before:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: firsttry
        name: FirstTry
        entry: bash -c 'firsttry run --gate pre-commit'
        language: system
```

**After:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: firsttry
        name: FirstTry
        entry: bash -lc 'PYTHONPATH=src python -m firsttry.cli run fast --show-report'
        language: system
```

### 2. GitHub Actions

**Before:**
```yaml
- name: FirstTry pre-commit checks
  run: python -m firsttry run --gate pre-commit
```

**After:**
```yaml
- name: FirstTry pre-commit checks
  env:
    PYTHONPATH: src
  run: python -m firsttry.cli run fast --show-report
```

### 3. CI Scripts

**Before:**
```bash
#!/bin/bash
python -m firsttry run --gate strict --require-license
```

**After:**
```bash
#!/bin/bash
export PYTHONPATH=src
python -m firsttry.cli run strict --tier pro --show-report
```

### 4. Makefile Targets

**Before:**
```makefile
check:
	python -m firsttry run --gate strict --require-license
```

**After:**
```makefile
check:
	PYTHONPATH=src python -m firsttry.cli run strict --tier pro --show-report
```

## Mode Reference

### Modes (Tier Predicates)

| Mode | Alias | Tier | Purpose |
|---|---|---|---|
| `auto` | (default) | free-lite | Fastest checks only (ruff) |
| `fast` | `q` | free-lite | Fast checks (ruff only) |
| `strict` | (none) | free-strict | Strict checks (ruff + mypy + pytest) |
| `ci` | `c` | free-strict | CI equivalent to strict |
| `config` | (none) | free-strict | Use firsttry.toml settings |
| `pro` | `p`, `teams`, `full` | pro | Professional tier features |
| `promax` | `e`, `enterprise` | promax | Enterprise tier features |

### Tier System

| Tier | Free? | Features |
|---|---|---|
| `free-lite` | ✅ | ruff only |
| `free-strict` | ✅ | ruff + mypy + pytest |
| `pro` | ❌ | full suite + team features |
| `promax` | ❌ | enterprise suite |

## Examples

### Run default (fast) checks
```bash
PYTHONPATH=src python -m firsttry.cli run
# or explicitly:
PYTHONPATH=src python -m firsttry.cli run fast
```

### Run strict checks
```bash
PYTHONPATH=src python -m firsttry.cli run strict
```

### Run with report
```bash
PYTHONPATH=src python -m firsttry.cli run --show-report
PYTHONPATH=src python -m firsttry.cli run strict --show-report
```

### Run with pro tier
```bash
PYTHONPATH=src python -m firsttry.cli run --tier pro
# or use mode alias:
PYTHONPATH=src python -m firsttry.cli run pro
```

### Run on changed files only
```bash
PYTHONPATH=src python -m firsttry.cli run --changed-only
PYTHONPATH=src python -m firsttry.cli run strict --changed-only
```

### Dry-run (preview what would run)
```bash
PYTHONPATH=src python -m firsttry.cli run --dry-run
```

### Generate JSON report
```bash
PYTHONPATH=src python -m firsttry.cli run --report-json .firsttry/report.json
```

## Environment Setup

Always set `PYTHONPATH` when using `python -m firsttry.cli`:

```bash
# For src/ layout repositories
export PYTHONPATH=src

# Disable slow pytest plugins if running tests
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
```

## Deprecation Timeline

**Current Status:** Legacy flags work with deprecation notices  
**Timeline:**
- **Now - Dec 2025:** Backward compat shim active, deprecation warnings printed
- **Jan 2026:** Consider removing legacy flag support

## Testing

Legacy compatibility is tested in `tests/test_cli_legacy_flags.py`:

```bash
# Run legacy compatibility tests
pytest tests/test_cli_legacy_flags.py -v
```

## Support

For questions about the migration:
1. Check this guide: https://docs.firsttry.com/cli-migration
2. Review examples in: `demo_legacy_compat.py`
3. Run: `firsttry run --help` for current CLI docs

## Troubleshooting

### "DEPRECATED" warning appears
This is expected for legacy commands. Update your scripts to use the new mode-based CLI when convenient.

### Command not found: firsttry
Ensure PYTHONPATH is set:
```bash
export PYTHONPATH=src
python -m firsttry.cli run
```

### License error with --tier pro
Ensure you have a valid FirstTry license. The old `--require-license` flag is now implicit in the tier selection.

## Quick Commands Reference

```bash
# Explore available commands
firsttry --help
firsttry run --help

# Check your environment
firsttry doctor

# List available checks
firsttry list-checks

# Initialize config
firsttry init

# View last report
firsttry inspect report
```

---

**Last Updated:** November 5, 2025  
**Status:** Backward-compat shim v1 active
