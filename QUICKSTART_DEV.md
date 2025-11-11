# FirstTry Development Quickstart
**Updated:** November 11, 2025  
**Status:** ✅ Production Ready (Zero Type Errors, Zero Lint Errors)

---

## 🚀 One-Command Setup

```bash
# Install dev dependencies (pinned versions)
pip install -r requirements-dev.txt

# Run entire dev suite (fast, deterministic, no hangs)
make dev.all
# OR
./scripts/dev_fast.sh
```

---

## 🎯 Fast Development Workflows

### Option 1: Makefile Targets (Recommended)

```bash
make dev.fast     # 20s  - Smoke tests + CLI ping
make dev.tests    # 120s - Fast test suite
make dev.checks   # 180s - Parallel linting + type-checking + coverage
make dev.all      # 300s - Everything above
```

### Option 2: Standalone Script

```bash
./scripts/dev_fast.sh  # Same as 'make dev.all', no Make required
```

---

## 🛡️ Deterministic Defaults (No Hangs)

Add to your shell RC (`~/.bashrc` / `~/.zshrc`):

```bash
# Speed + determinism
export PYTHONHASHSEED=0
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1   # Avoids slow/global plugins
export FT_SKIP_TOOL_EXEC=1                # FirstTry safe test mode
```

---

## 📊 Current Status

```bash
$ mypy src
Success: no issues found in 153 source files

$ ruff check src
All checks passed!

$ make dev.all
>>> All dev routines complete (fast, timed, reliable)
```

---

## 🔧 What Was Fixed (Nov 11, 2025)

| Issue | Fix | Files |
|-------|-----|-------|
| Mypy type error | Added `_to_str()` helper | `src/firsttry/utils/proc.py` |
| Unused import | Removed `Tuple` | `src/firsttry/lazy_orchestrator.py` |
| Missing tools | Added isort, pytest-cov, bandit | `requirements-dev.txt` |
| No fast workflow | Created Makefile targets + script | `Makefile`, `scripts/dev_fast.sh` |

**Full Details:** `.firsttry/AUDIT_FIXES_APPLIED.md`

---

## 📚 Documentation Index

| Document | Purpose |
|----------|---------|
| `docs/AUDIT_SYSTEM.md` | Audit system usage guide |
| `.firsttry/AUDIT_REPORT_COMPREHENSIVE.md` | Complete audit findings |
| `.firsttry/AUDIT_FIXES_APPLIED.md` | Fix implementation details |
| `scripts/ft_audit_readonly.sh` | Drop-in audit script |
| `.github/workflows/readonly-audit-example.yml` | CI audit template |

---

## ⚡ Key Features

- ✅ **Hard timeouts**: Every command bounded (no infinite hangs)
- ✅ **Parallel execution**: Linters run concurrently
- ✅ **Tool-aware**: Gracefully skips missing tools
- ✅ **Deterministic**: Same results every time
- ✅ **Non-blocking**: Coverage never fails the build
- ✅ **Fast**: Complete dev check in <5 minutes

---

## 🎓 For New Team Members

```bash
# 1. Clone repo
git clone <repo-url>
cd Firstry

# 2. Install dependencies
pip install -r requirements-dev.txt

# 3. Verify everything works
make dev.all

# 4. Before committing
make dev.checks
```

---

**Questions?** See `.firsttry/AUDIT_FIXES_APPLIED.md` for detailed explanations.
