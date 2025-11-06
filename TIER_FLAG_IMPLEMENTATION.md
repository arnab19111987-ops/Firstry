# Implementation Summary: --tier Flag Support

## Changes Made

### 1. Updated `cmd_run()` in `src/firsttry/cli.py`

**Change**: Modified the argument parser to prioritize `--tier` as a named flag while maintaining backward compatibility with positional tier argument.

**Before**:
```python
p.add_argument("maybe_tier", nargs="?", help="tier/profile (e.g., free-lite, lite, pro)")
p.add_argument("--tier", help="tier/profile (alias of positional)")
```

**After**:
```python
p.add_argument("maybe_tier", nargs="?", help=argparse.SUPPRESS)  # hidden positional for backward compat
p.add_argument("--tier", help="tier/profile (e.g., free-lite, lite, pro, strict)")
```

**Priority order**:
1. `--tier` flag (primary interface)
2. Positional argument (hidden, backward compatibility)
3. Default value: `"lite"`

### 2. Created `.venv/bin/ft` Launcher Script

**Location**: `/workspaces/Firstry/.venv/bin/ft`

**Contents**:
```bash
#!/usr/bin/env bash
export PYTHONPATH=src
exec python -m firsttry.cli "$@"
```

**Permissions**: Executable (`chmod +x`)

**Purpose**: Provides a simple wrapper that automatically sets `PYTHONPATH=src` for convenient local development without requiring package installation.

### 3. Verified Entry Points in `pyproject.toml`

**Entry points already configured**:
```toml
[project.scripts]
firsttry = "firsttry.cli:main"
ft = "firsttry.cli_aliases:main"
```

These enable:
- `firsttry run --tier <tier>` (after `pip install -e .`)
- `ft <command>` (predefined alias shortcuts)

## Usage Examples

### Recommended Usage (--tier flag)

```bash
# Using shell alias
alias ft='PYTHONPATH=src python -m firsttry.cli'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ft run --tier free-lite --show-report

# Direct Python invocation
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python -c "import firsttry.cli as c; c.cmd_run(['--tier','free-lite','--show-report'])"

# Using the wrapper script
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/ft run --tier free-lite --show-report

# After pip install -e .
firsttry run --tier free-lite --show-report
```

### Available Tiers

- `free-fast` - Minimal free tier
- `free-lite` - Free tier (ruff + pytest)
- `lite` - Standard tier (ruff + mypy + pytest)
- `pro` - Pro tier (requires license)
- `strict` - All checks enabled

### Backward Compatibility

The following still work:

```bash
# Positional tier (hidden in help)
PYTHONPATH=src python -m firsttry.cli run lite

# Mode-based (maps to tier internally)
PYTHONPATH=src python -m firsttry.cli run fast
PYTHONPATH=src python -m firsttry.cli run strict
```

## Testing

Created comprehensive test suite in `test_tier_flag.sh`:

✅ Module import verification
✅ Direct `cmd_run()` call with `--tier` flag
✅ Python module invocation: `python -m firsttry.cli run --tier`
✅ Wrapper script: `.venv/bin/ft run --tier`
✅ Help output verification
✅ Backward compatibility with positional tier

**All tests passing!**

## Files Modified

1. `src/firsttry/cli.py` - Updated `cmd_run()` function
2. `.venv/bin/ft` - Created launcher script (new file)
3. `TIER_FLAG_USAGE_GUIDE.md` - Usage documentation (new file)
4. `test_tier_flag.sh` - Test suite (new file)

## Benefits

1. **Cleaner CLI**: `--tier` is more explicit than positional arguments
2. **Backward Compatible**: Existing scripts using positional tier still work
3. **Multiple Access Methods**: Shell alias, wrapper script, or installed package
4. **Well Documented**: Comprehensive usage guide and test coverage
5. **Flexible Development**: Works both in-repo (PYTHONPATH=src) and installed (pip install -e .)

## Next Steps (Optional)

1. Update any existing documentation to recommend `--tier` flag
2. Add deprecation warnings for positional tier usage (in a future release)
3. Update CI/CD pipelines to use `--tier` flag explicitly
