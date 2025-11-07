# ⚠️ Configuration Migration Impact Report

**Date:** November 7, 2025  
**Status:** ⛔ **CRITICAL BREAKING ISSUES DETECTED**  
**Recommendation:** **DO NOT** replace `src/firsttry/config.py`

---

## Executive Summary

The proposed configuration system (license + S3) would **break the entire codebase** if it replaced the existing `src/firsttry/config.py`. 

### Key Issues:
1. ❌ Function signature mismatch (breaking existing calls)
2. ❌ Return type completely different (breaks all accessors)
3. ❌ Helper functions disappear (breaks imports)
4. ❌ Workflow configuration lost (breaks DAG system)

**Solution:** Create a **separate** file (`license_config.py`) instead of replacing.

---

## Detailed Breaking Issues

### Issue #1: Function Signature Mismatch 🔴

**Current (Existing) Code:**
```python
def load_config(repo_root: Path) -> Config:
    path = repo_root / "firsttry.toml"
    ...
```

**Proposed (Replacement) Code:**
```python
def load_config() -> AppCfg:
    cfg: AppCfg = {}
    ...
```

**Impact on Existing Code:**

File: `src/firsttry/run_swarm.py` (line 5)
```python
from .config import load_config
# ... later ...
cfg = load_config(repo_root)  # ❌ BREAKS!
# TypeError: load_config() takes 0 positional arguments but 1 was given
```

**Severity:** 🔴 **CRITICAL** — Immediate runtime failure

---

### Issue #2: Return Type Completely Different 🔴

**Current (Existing) Type:**
```python
@dataclass
class Config:
    tier: str = "lite"
    remote_cache: bool = False
    workers: int = 8
    timeouts: Timeouts = field(default_factory=Timeouts)
    checks_flags: dict[str, list[str]] = field(default_factory=dict)
    workflow: Workflow = field(default_factory=Workflow)
```

**Proposed (Replacement) Type:**
```python
class AppCfg(TypedDict, total=False):
    license: LicenseCfg
    s3: S3Cfg
```

**Current Usage in `run_swarm.py`:**
```python
cfg = load_config(repo_root)  # Now returns AppCfg (dict), not Config

# All these will CRASH:
cfg.tier                        # ❌ KeyError or AttributeError
cfg.timeouts.default            # ❌ KeyError (no 'timeouts' key)
cfg.checks_flags                # ❌ KeyError (no 'checks_flags' key)
cfg.workflow.pytest_depends_on  # ❌ KeyError (no 'workflow' key)
```

**Error Messages:**
```
AttributeError: 'dict' object has no attribute 'tier'
KeyError: 'timeouts'
KeyError: 'checks_flags'
KeyError: 'workflow'
```

**Severity:** 🔴 **CRITICAL** — Every config access fails

---

### Issue #3: Helper Functions Disappear 🔴

**Current Exports (from `config.py`):**
```python
✅ load_config(repo_root: Path) -> Config
✅ timeout_for(cfg: Config, check_id: str) -> int
✅ workflow_requires(cfg: Config) -> list[str]
```

**Proposed Exports (would NOT include):**
```python
✅ load_config() -> AppCfg
❌ NO timeout_for()
❌ NO workflow_requires()
```

**Current Usage in `run_swarm.py`:**
```python
from .config import load_config      # exists but WRONG signature
from .config import timeout_for      # ❌ WILL NOT EXIST
from .config import workflow_requires # ❌ WILL NOT EXIST

# Later in code:
timeout_for(cfg, 'ruff')            # ❌ NameError
workflow_requires(cfg)              # ❌ NameError
```

**Error Messages:**
```
ImportError: cannot import name 'timeout_for' from 'firsttry.config'
ImportError: cannot import name 'workflow_requires' from 'firsttry.config'
NameError: name 'timeout_for' is not defined
NameError: name 'workflow_requires' is not defined
```

**Severity:** 🔴 **CRITICAL** — Imports fail immediately

---

### Issue #4: Workflow Configuration Lost 🔴

**What Gets Lost:**

| Component | Current | Proposed | Impact |
|-----------|---------|----------|--------|
| Workflow timeouts | ✅ Supported | ❌ Gone | Cannot set task timeouts |
| Task dependencies | ✅ Supported | ❌ Gone | Cannot configure pytest/npm deps |
| Check-specific flags | ✅ Supported | ❌ Gone | Cannot pass ruff/mypy args |
| Remote cache config | ✅ Supported | ❌ Gone | Cannot enable remote caching |
| Worker pool size | ✅ Supported | ❌ Gone | Cannot tune parallelism |

**Example - What's Lost:**
```toml
# This config becomes USELESS:
[core]
tier = "pro"
workers = 4
remote_cache = true

[timeouts]
default = 300
per_check = {ruff = 10, mypy = 120, pytest = 300}

[workflow]
pytest_depends_on = ["ruff", "mypy"]

[checks.flags]
ruff = ["--select", "E,W"]
mypy = ["--strict"]
```

**Impact on DAG System:**
- Cannot run DAG (workflow dependencies lost)
- Cannot set timeouts (DAG executor needs this)
- Cannot configure tasks (all task config gone)

**Severity:** 🔴 **CRITICAL** — Core functionality lost

---

## Affected Code

### Direct Breakage

| File | Lines | Issue | Impact |
|------|-------|-------|--------|
| `src/firsttry/run_swarm.py` | 5-7 | Import fails + wrong signature | 🔴 Entire module broken |
| `src/firsttry/run_swarm.py` | ~20+ | All config accessors fail | 🔴 Runtime crashes |

### Indirect Breakage

Any code that:
- Imports `Config`, `Timeouts`, or `Workflow` — breaks
- Calls `timeout_for()` or `workflow_requires()` — breaks
- Accesses `.tier`, `.timeouts`, `.workflow`, `.checks_flags` — breaks

---

## Test Impact

**Current Test Suite Status:** ✅ 325 tests passing

**After Replacement:**
```
❌ Tests will FAIL immediately on import
❌ TypeError/ImportError in test_runner_dag.py
❌ Attribute errors when accessing config fields
❌ Complete test suite failure
```

---

## Safe Solution ✅

### Option A: Create New File (RECOMMENDED)

**Step 1: Keep existing `config.py`**
```
✅ UNCHANGED: src/firsttry/config.py (workflow/timeout config)
```

**Step 2: Create new `license_config.py`**
```
✅ NEW: src/firsttry/license_config.py (license/S3 config)
   Exports: load_license_config(), LicenseCfg, S3Cfg, s3_prefs()
```

**Step 3: Update imports in new files**
```python
# src/firsttry/s3_uploader.py
from .license_config import load_license_config  # ✅ CORRECT

# src/firsttry/doctor.py
from .license_config import load_license_config  # ✅ CORRECT
```

**Step 4: Keep existing imports working**
```python
# src/firsttry/run_swarm.py (NO CHANGES NEEDED)
from .config import load_config      # ✅ Still works
from .config import timeout_for      # ✅ Still works
from .config import workflow_requires # ✅ Still works
```

**Result:**
- ✅ Zero breaking changes
- ✅ All existing code works
- ✅ New license/S3 config available alongside
- ✅ Clear separation of concerns
- ✅ All 325 tests still pass

---

## Comparison Table

| Aspect | Replace (WRONG) | New File (CORRECT) |
|--------|-----------------|-------------------|
| **Existing Code Breaks?** | ❌ Yes, critical | ✅ No |
| **Test Suite Breaks?** | ❌ Yes, fatal | ✅ No |
| **Workflow Config Lost?** | ❌ Yes | ✅ No |
| **License Config Available?** | ✅ Yes | ✅ Yes |
| **S3 Config Available?** | ✅ Yes | ✅ Yes |
| **Backward Compatible?** | ❌ No | ✅ Yes |
| **Migration Effort?** | ⚠️ Rewrite everything | ✅ Add new file only |

---

## Recommendation

### ✅ **APPROVED**: New File Approach

**Action Items:**
1. ✅ Create `src/firsttry/license_config.py` (your proposed code)
2. ✅ Leave `src/firsttry/config.py` **UNCHANGED**
3. ✅ Update `s3_uploader.py` to import from `license_config`
4. ✅ Update `doctor.py` to import from `license_config`
5. ✅ Add `__main__.py` router for `python -m firsttry doctor`
6. ✅ Verify no test failures

**Files to Touch:**
- ✅ CREATE: `src/firsttry/license_config.py`
- ✅ CREATE: `src/firsttry/s3_uploader.py`
- ✅ CREATE: `src/firsttry/doctor.py`
- ✅ CREATE: `src/firsttry/__main__.py`
- ✅ KEEP: `src/firsttry/config.py` (no changes)

**Files NOT to Touch:**
- 🚫 DO NOT modify `src/firsttry/config.py`
- 🚫 DO NOT modify `src/firsttry/run_swarm.py`

---

## Checklist Before Deployment

- [ ] Create `license_config.py` with license+S3 logic
- [ ] Create `s3_uploader.py` with your S3 code
- [ ] Create `doctor.py` with your diagnostic code
- [ ] Create `__main__.py` router
- [ ] Verify imports use `license_config` (not `config`)
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Verify: `python -m firsttry doctor` works
- [ ] Verify: `run_swarm.py` still imports correctly
- [ ] Verify: No test failures

---

## Conclusion

**DO NOT replace `src/firsttry/config.py`**

Creating a new `license_config.py` file is:
- ✅ Zero breaking changes
- ✅ Fully backward compatible
- ✅ Clear separation of concerns
- ✅ Safe and reviewable
- ✅ Maintains 325+ passing tests

---

**Status:** ⛔ **BLOCK on replacement approach**  
**Recommendation:** ✅ **APPROVE new file approach**

---

*Generated: 2025-11-07 after comprehensive code impact analysis*
