# FirstTry --tier Flag Usage Guide

The `--tier` flag is now the primary way to specify the tier/profile when running FirstTry checks via the DAG-based execution system.

## Quick Start

### Using the alias (in your repo root with venv)

```bash
# stay in your repo root and venv
alias ft='PYTHONPATH=src python -m firsttry.cli'

# run via DAG with explicit tier
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ft run --tier free-lite --show-report

# or
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ft run --tier lite --show-report
```

### Direct Python call (bypassing argument parsing issues)

If you encounter parsing weirdness, call the run dispatcher directly:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python -c "import firsttry.cli as c; c.cmd_run(['--tier','free-lite','--show-report'])"
```

## Durable Setup (One-time Wrapper)

### Create a tiny ft launcher inside your venv

```bash
cat > .venv/bin/ft <<'SH'
#!/usr/bin/env bash
export PYTHONPATH=src
exec python -m firsttry.cli "$@"
SH
chmod +x .venv/bin/ft

# now this works:
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/ft run --tier free-lite --show-report
```

✅ **Already created!** The launcher script is now at `.venv/bin/ft`

## Using the Installed Package (via pip install -e .)

If your project defines entry points (which it does in `pyproject.toml`), install it editable:

```bash
pip install -e .

# then use the firsttry command directly:
firsttry run --tier free-lite --show-report

# or the ft alias:
ft lite  # uses the cli_aliases.py predefined profiles
```

## Sanity Checks

### Confirm module import path

```bash
PYTHONPATH=src python -c "import firsttry, sys; print('ok from', firsttry.__file__); print(sys.executable)"
```

### See run help (shows accepted flags)

```bash
PYTHONPATH=src python -m firsttry.cli run --help
```

## Available Tiers

- `free-fast` - Fastest free tier (minimal checks)
- `free-lite` - Free tier with ruff + pytest
- `lite` - Standard tier with ruff + mypy + pytest
- `pro` - Pro tier with additional checks (requires license)
- `strict` - Strict mode with all available checks

## Examples

### Running with different tiers

```bash
# Free lite tier (fast, just ruff + pytest)
PYTHONPATH=src python -m firsttry.cli run --tier free-lite --show-report

# Lite tier (ruff + mypy + pytest)
PYTHONPATH=src python -m firsttry.cli run --tier lite --show-report

# Strict mode (all checks)
PYTHONPATH=src python -m firsttry.cli run --tier strict --show-report
```

### Using the wrapper script

```bash
# Via the .venv/bin/ft wrapper
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/ft run --tier free-lite --show-report

# Via the installed command (after pip install -e .)
firsttry run --tier free-lite --show-report
```

### Additional flags

```bash
# Show detailed report
PYTHONPATH=src python -m firsttry.cli run --tier lite --show-report

# Write JSON report
PYTHONPATH=src python -m firsttry.cli run --tier lite --report-json .firsttry/report.json

# Run only changed files
PYTHONPATH=src python -m firsttry.cli run --tier lite --changed-only

# Disable caching
PYTHONPATH=src python -m firsttry.cli run --tier lite --no-cache
```

## Backward Compatibility

The --tier flag is now the primary interface, but the following still work for backward compatibility:

```bash
# Positional tier (hidden in help but still supported)
PYTHONPATH=src python -m firsttry.cli run lite --show-report

# Mode-based (maps to tier internally)
PYTHONPATH=src python -m firsttry.cli run fast
PYTHONPATH=src python -m firsttry.cli run strict
PYTHONPATH=src python -m firsttry.cli run ci
```

## Implementation Notes

- The `cmd_run` function in `cli.py` now accepts `--tier` as a named flag
- A hidden positional argument is kept for backward compatibility
- Priority order: `--tier` flag > positional argument > default (`lite`)
- The entry points `firsttry` and `ft` are defined in `pyproject.toml`
- The `.venv/bin/ft` wrapper sets `PYTHONPATH=src` automatically
