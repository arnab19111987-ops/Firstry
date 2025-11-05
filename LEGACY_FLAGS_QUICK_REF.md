# Quick Reference: Legacy Flag Backward Compatibility

## One-Liner Cheat Sheet

```bash
# OLD (still works!)                    # NEW (recommended)
firsttry run --gate pre-commit          firsttry run fast
firsttry run --gate ruff                firsttry run fast
firsttry run --gate strict              firsttry run strict
firsttry run --gate ci                  firsttry run ci
firsttry run --require-license          firsttry run --tier pro
firsttry run --gate strict \            firsttry run strict \
  --require-license                       --tier pro
```

## What You Get

✅ **Zero-churn migration** - Old commands work unchanged  
✅ **Deprecation notices** - User-friendly guidance to modern CLI  
✅ **Full test coverage** - 21 comprehensive tests, all passing  
✅ **No performance impact** - Minimal O(n) translation at CLI entry  
✅ **Safe defaults** - Unknown gates map to conservative fast mode  

## How It Works

```
Your old command
     ↓
CLI receives argv
     ↓
_translate_legacy_args() translates flags
     ↓
cmd_run() processes modern form
     ↓
Works exactly as modern CLI would
     + Deprecation notice printed to stderr
```

## Translation Rules

| Legacy Input | Maps To | Logic |
|---|---|---|
| `--gate pre-commit` | `fast` | Pre-commit is fast check |
| `--gate ruff` | `fast` | Ruff is fastest check |
| `--gate strict` | `strict` | Named exactly for this tier |
| `--gate ci` | `strict` | CI equivalent to strict |
| `--gate mypy` | `strict` | Part of strict suite |
| `--gate pytest` | `strict` | Part of strict suite |
| `--gate <unknown>` | `fast` | Safe default |
| `--require-license` | `--tier pro` | License implies pro tier |

## Real Examples

### Pre-commit Hook

```yaml
# Before (still works)
- repo: local
  hooks:
    - id: firsttry
      entry: bash -c 'firsttry run --gate pre-commit'
      language: system

# After (recommended)
- repo: local
  hooks:
    - id: firsttry
      entry: bash -lc 'PYTHONPATH=src python -m firsttry.cli run fast'
      language: system
```

### GitHub Actions

```yaml
# Before (still works, with deprecation warning)
- run: python -m firsttry run --gate strict --require-license

# After (recommended)
- run: |
    export PYTHONPATH=src
    python -m firsttry.cli run strict --tier pro --show-report
```

### Shell Scripts

```bash
#!/bin/bash
# Before (still works)
python -m firsttry run --gate pre-commit --require-license

# After (recommended)
export PYTHONPATH=src
python -m firsttry.cli run fast --tier pro --show-report
```

## Migration Checklist

- [ ] Review your firsttry invocations (`grep -r "firsttry run" .`)
- [ ] Find all `--gate` and `--require-license` usages
- [ ] Plan migration to new CLI (no rush - backward compat active)
- [ ] Update .pre-commit-config.yaml
- [ ] Update GitHub Actions workflows
- [ ] Update CI scripts
- [ ] Update shell aliases/functions
- [ ] Test with modern CLI
- [ ] Commit changes

## Testing Your Migration

```bash
# Old command - verify it still works with deprecation warning
PYTHONPATH=src python -m firsttry.cli run --gate pre-commit

# New command - verify modern form works
PYTHONPATH=src python -m firsttry.cli run fast

# Both should behave identically (except for stderr warning)
```

## Need Help?

1. **See all available commands:** `firsttry --help`
2. **See all run options:** `firsttry run --help`
3. **Read full migration guide:** `CLI_MIGRATION_GUIDE.md`
4. **See code examples:** `demo_legacy_compat.py`
5. **Run tests:** `pytest tests/test_cli_legacy_flags.py -v`

## Key Points

- **Old CLI still works** - No breaking changes
- **Deprecation printed** - Users see helpful guidance  
- **Fully tested** - 21 tests covering all scenarios
- **Safe migration** - No rush to update
- **Clear path forward** - Migration guide provided

## Deprecation Notice Example

```
$ PYTHONPATH=src python -m firsttry.cli run --gate pre-commit
[firsttry] DEPRECATED: --gate/--require-license are no longer supported.
           Use 'run <mode>' (fast|strict|pro|enterprise) or '--tier <tier>' instead.
           See: https://docs.firsttry.com/cli-migration

✅ [OK   ] ruff 145ms hit-local
✅ All checks passed!
```

## Status

- ✅ Backward-compat shim implemented
- ✅ 21 tests passing (100%)
- ✅ Zero impact on modern CLI
- ✅ Deprecation notices active
- ✅ Documentation complete
- ✅ Ready for production use

---

**Implementation Date:** November 5, 2025  
**Commit:** 94196cb  
**Tests:** 21/21 passing ✅
