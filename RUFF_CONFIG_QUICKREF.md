# Quick Reference: Dual Ruff Config

## Files

| File | Purpose | Rules |
|------|---------|-------|
| `.ruff.toml` | Baseline (everywhere) | E, F, I (essential only) |
| `.ruff.pre-commit.toml` | Strict (pre-commit only) | ALL + preview |
| `.pre-commit-config.yaml` | Hook configuration | Points to strict config |

## Commands

### Local Development
```bash
ruff check .              # Check with baseline
ruff check . --fix        # Auto-fix baseline issues
ruff format .             # Format code
```

### Pre-commit
```bash
pre-commit install        # Install hooks
pre-commit run --all-files # Run all hooks
pre-commit run ruff --all-files  # Just ruff strict
```

### Git Workflow
```bash
git add .
git commit -m "msg"       # Hook runs strict config
# If fixes made, review and re-commit
```

## Key Differences

| Aspect | Baseline | Strict |
|--------|----------|--------|
| **Config file** | `.ruff.toml` | `.ruff.pre-commit.toml` |
| **Rules** | E, F, I | ALL |
| **Preview** | No | Yes |
| **Auto-fix** | Manual via `--fix` | Automatic |
| **Exit code** | 0 if passed | Non-zero if fixes made |
| **When used** | Always (local + CI) | Pre-commit only |

## Baseline Rules (E, F, I)

- **E**: Pycodestyle (whitespace, indentation, line length)
- **F**: Pyflakes (undefined names, unused imports)
- **I**: isort (import sorting/formatting)

## Strict Rules (ALL)

Baseline + 50+ additional rule families:
- **D**: Docstrings
- **A**: Shadowed builtins
- **C**: Complexity
- **T**: Print statements
- **RUF**: Ruff-specific
- ...and more

## Troubleshooting

**Hook fails with auto-fixes?** This is intentional—review and re-commit.

**Want to ignore a rule?** Edit `.ruff.pre-commit.toml`:
```toml
[lint]
ignore = ["D203"]
```

**Check configuration?**
```bash
ruff show-settings --config=.ruff.toml              # Baseline
ruff show-settings --config=.ruff.pre-commit.toml   # Strict
```

**Bypass hook temporarily?**
```bash
git commit --no-verify   # (not recommended!)
```

See `RUFF_CONFIG_GUIDE.md` for complete documentation.
