# FirstTry --tier Flag Quick Reference

## TL;DR - Copy & Paste Commands

```bash
# Setup (one-time)
cat > .venv/bin/ft <<'SH'
#!/usr/bin/env bash
export PYTHONPATH=src
exec python -m firsttry.cli "$@"
SH
chmod +x .venv/bin/ft

# Or install editable
pip install -e .
```

## Running with --tier Flag

```bash
# Method 1: Direct Python call (most reliable)
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python -c "import firsttry.cli as c; c.cmd_run(['--tier','free-lite','--show-report'])"

# Method 2: Module invocation
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src python -m firsttry.cli run --tier free-lite --show-report

# Method 3: Wrapper script
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/ft run --tier free-lite --show-report

# Method 4: Installed package
firsttry run --tier free-lite --show-report
```

## Shell Alias (Recommended)

```bash
# Add to ~/.bashrc or ~/.zshrc
alias ft='PYTHONPATH=src python -m firsttry.cli'

# Then use:
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ft run --tier free-lite --show-report
```

## Common Tier Values

- `free-lite` - Fast free tier (ruff + pytest)
- `lite` - Standard (ruff + mypy + pytest)
- `strict` - All checks enabled
- `pro` - Pro features (requires license)

## Useful Flags

```bash
--show-report              # Display detailed console output
--report-json PATH         # Save JSON report
--changed-only            # Only check changed files
--no-cache                # Disable caching
--dry-run                 # Preview without execution
```

## Sanity Checks

```bash
# Verify module import
PYTHONPATH=src python -c "import firsttry, sys; print('ok from', firsttry.__file__)"

# Check help
PYTHONPATH=src python -m firsttry.cli run --help | grep -A2 "\-\-tier"
```

## Example Workflows

```bash
# Fast dev loop (ruff only)
.venv/bin/ft run --tier free-lite

# Pre-commit (ruff + mypy + pytest)
.venv/bin/ft run --tier lite --show-report

# CI simulation (all checks)
.venv/bin/ft run --tier strict --report-json .firsttry/report.json

# Changed files only
.venv/bin/ft run --tier lite --changed-only
```
