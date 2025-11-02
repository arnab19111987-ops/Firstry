# FirstTry Capability and Health Audit Report

```json
{
  "name": "FirstTry",
  "branch": "feat/ci-parity-mvp",
  "report_date": "2025-11-01",
  "commands_tested": ["inspect", "sync", "version", "run", "status", "setup", "doctor", "report"],
  "failed_commands": ["status", "setup", "doctor", "report", "run --level"]
}
```

## Executive Summary

FirstTry 0.5.0 is a **partially functional** local CI runner with **4 working core commands** but **significant CLI architecture gaps**. The project has **strong license/trial infrastructure** and **comprehensive git hook integration**, but **42 failing tests** indicate **incomplete refactoring** from legacy CLI structure. **Immediate fixes needed** for legacy command compatibility and test stabilization.

---

## Command Inventory

### ✅ **Working Commands**
| Command | Expected Behavior | Status |
|---------|-------------------|---------|
| `firsttry --help` | Show main help menu | ✅ **WORKS** (0.121s) |
| `firsttry version` | Display version 0.5.0 | ✅ **WORKS** (0.121s) |  
| `firsttry inspect` | Show repo context, config, plan | ✅ **WORKS** (0.318s) |
| `firsttry sync` | Sync CI files → firsttry.toml | ✅ **WORKS** (0.159s) |

### ❌ **Failed Commands**
| Command | Expected Behavior | Failure Output |
|---------|-------------------|----------------|
| `firsttry status` | Show system health | `error: invalid choice: 'status'` |
| `firsttry setup` | Initialize hooks + config | `error: invalid choice: 'setup'` |
| `firsttry doctor` | System diagnostics | `error: invalid choice: 'doctor'` |
| `firsttry report` | Generate reports | `error: invalid choice: 'report'` |
| `firsttry run --level 1/2` | Run checks by level | `error: unrecognized arguments: --level` |

### 🔍 **CLI Architecture Analysis**
**Primary CLI Parser:** `src/firsttry/cli.py:19-48`
```python
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="firsttry", ...)
    sub = p.add_subparsers(dest="cmd", required=True)
    # Only defines: run, inspect, sync, version
```

**Legacy CLI Implementation:** `src/firsttry/cli_enhanced_old.py:397-450` (758 lines)
- Contains `handle_setup`, `handle_status`, `handle_doctor` functions
- **NOT WIRED** into current CLI parser
- References `--level` argument system **missing from current CLI**

---

## License and Trial Logic

### 📍 **License Enforcement Locations**

**1. Core License Guard** - `src/firsttry/license_guard.py:1-34`
```python
def get_tier() -> str:
    # FIRSTTRY_TIER=teams → "teams" 
    # FIRSTTRY_TIER=developer → "developer" (default)
    # Legacy: free→developer, pro→teams
```

**2. License Cache System** - `src/firsttry/license_cache.py:13-95`
```python
CACHE_PATH = Path("~/.firsttry/license.json")
def assert_license(product="firsttry") -> Tuple[bool, list[str], str]:
    # Network validation via FIRSTTRY_LICENSE_URL
    # 7-day cache freshness (FRESH_FOR = timedelta(days=7))
```

**3. Network License Verification** - `src/firsttry/license_cache.py:57-67`
```python
def remote_verify(base_url: str, product: str, key: str):
    # POST to {base_url}/v1/license/verify
    # Timeout: 10 seconds
    # Uses urllib.request (blocking network call)
```

**4. Trial License System** - `src/firsttry/license_trial.py`  
```python
TRIAL_FILE = Path.home() / ".firsttry" / "license_trial.json"
# Generates 3-day trials automatically
```

### 🔧 **License Cache Paths**
- **Primary:** `~/.firsttry/license.json` (license_cache.py:13)
- **Trial:** `~/.firsttry/license_trial.json` (license_trial.py)
- **Legacy:** `~/.firsttry_license` (licensing.py:49)
- **XDG Support:** `$XDG_CACHE_HOME/firsttry/license.json` (licensing.py:36)

---

## Git Hook Integration

### 📍 **Hook Installation Code**

**Primary Hook Installer** - `src/firsttry/hooks.py:50-59`
```python
def install_git_hooks(repo_root: str | Path = ".") -> Tuple[Path, Path]:
    hooks_dir = repo_root / ".git" / "hooks"
    pre_commit_path = hooks_dir / "pre-commit"
    pre_push_path = hooks_dir / "pre-push" 
    _write_executable(pre_commit_path, PRE_COMMIT_SCRIPT)
    _write_executable(pre_push_path, PRE_PUSH_SCRIPT)
```

**Hook Script Templates** - `src/firsttry/hooks.py:10-35`
```bash
# PRE_COMMIT_SCRIPT calls: firsttry run --level 2
# PRE_PUSH_SCRIPT calls: firsttry run --level 3
# ⚠️ PROBLEM: --level flag doesn't exist in current CLI
```

**Bootstrap Function** - `src/firsttry/hooks.py:62-85`
```python
def install_hooks_and_bootstrap_trial(repo_root):
    install_git_hooks(repo_root)
    lic_obj = ensure_trial_license_if_missing(days=3)
    # Provides user onboarding messages
```

---

## Configuration Files

### 📋 **Recognized Config Files**
1. **`./firsttry.toml`** - Primary config ✅ **EXISTS**
2. **`./pyproject.toml` [tool.firsttry]** - Secondary config ✅ **EXISTS** 
3. **`.firsttry.yml/.firsttry.yaml`** - Legacy format (code refs but no files found)

### 📄 **Current Config Content** - `./firsttry.toml`
```toml
[tool.firsttry]
fail_on_drift = true

[tool.firsttry.run]
tools = ["black", "ci-parity", "mypy", "npm test", "pytest", "ruff"]

[tool.firsttry.tool.ruff]
cmd = "ruff check ."
# ... (tool-specific commands defined)
```

**Config Loading Logic:** `src/firsttry/config_loader.py:15-45`

---

## Test Results Analysis

### 📊 **Test Summary**
- **Total Tests:** 240
- **Passed:** 189 (78.75%)
- **Failed:** 42 (17.5%) 
- **Skipped:** 9 (3.75%)
- **Runtime:** 3.57 seconds

### 🚨 **Critical Test Failures**
```
FAILED tests/test_cli_comprehensive.py::test_cli_mirror_ci_*
FAILED tests/test_cli_doctor_and_license.py::test_cli_doctor_*
FAILED tests/test_cli_run.py::test_cli_run_*
FAILED tests/test_cli_runner_loader.py::test_*_runners_*
```

**Root Cause:** CLI architecture mismatch between current parser (4 commands) and test expectations (legacy 8+ commands)

---

## External Network Dependencies

### 🌐 **Network Call Analysis**

**License Verification** - `src/firsttry/license_cache.py:57-67`  
⚠️ **HIGH RISK:** Blocking network calls during CLI startup
- URL: `FIRSTTRY_LICENSE_URL` environment variable
- Timeout: 10 seconds  
- Triggers: Any CLI command execution in pro/teams mode

**Docker Health Checks** - `src/firsttry/docker_smoke.py:15-25`
- URL: Configurable health check endpoints
- Timeout: Configurable
- Triggers: Only when `docker_smoke` checks run

**Dependency Audit** - Usage in code suggests `pip-audit` integration
- Likely external package vulnerability database calls
- Not currently working (`pip-audit: not found`)

---

## Quick Fix Recommendations

### 🔧 **Immediate Fixes (1-2 lines each)**

**1. Fix Legacy Commands** - `src/firsttry/cli.py:25`
```python
# ADD after line 47:
p_status = sub.add_parser("status", help="Show system status")
p_setup = sub.add_parser("setup", help="Initialize FirstTry")  
p_doctor = sub.add_parser("doctor", help="System diagnostics")
```

**2. Fix Run Command Level Args** - `src/firsttry/cli.py:28`
```python
# ADD to p_run arguments:
p_run.add_argument("--level", type=int, choices=[1,2,3], help="Run level")
```

**3. Fix Hook Scripts** - `src/firsttry/hooks.py:10,24`
```bash
# CHANGE: firsttry run --level 2
# TO:     firsttry run --profile fast  
```

**4. Skip Network in Tests** - Add to pytest setup:
```python
monkeypatch.setenv("FIRSTTRY_LICENSE_URL", "")  # Disable license network calls
```

---

## Risky Assumptions

### ⚠️ **High Risk**
1. **License Server Dependency:** CLI may hang 10s if `FIRSTTRY_LICENSE_URL` is unreachable
2. **Git Hooks Call Non-existent --level:** Hooks will fail on commit/push
3. **Test Suite Brittleness:** 17.5% failure rate suggests unstable CI pipeline

### ⚠️ **Medium Risk**  
1. **Config File Precedence:** Multiple config sources (firsttry.toml, pyproject.toml) without clear precedence docs
2. **Trial License Auto-generation:** May create files in `~/.firsttry/` without user consent  
3. **Import Path Assumptions:** Code uses both `firsttry.cli` and `firsttry` imports inconsistently

---

## Remediation Plan

### 🎯 **Phase 1: Critical Stability (Week 1)**

**Task 1:** Restore Legacy CLI Commands *(2 hours)*
- File: `src/firsttry/cli.py`  
- Add: status, setup, doctor, report subparsers
- Wire: to handlers in `cli_enhanced_old.py`

**Task 2:** Fix Git Hook --level References *(1 hour)*
- File: `src/firsttry/hooks.py`
- Replace: `--level 2/3` with `--profile fast`
- Test: hooks actually work after install

**Task 3:** Add --level to Run Command *(1 hour)*  
- File: `src/firsttry/cli.py`
- Add: `--level` argument to run parser
- Map: level → profile in handler

**Task 4:** Stabilize License Network Calls *(2 hours)*
- File: `src/firsttry/license_cache.py`  
- Add: `--offline` mode flag
- Default: skip network if env vars missing

**Task 5:** Fix Critical Test Failures *(4 hours)*
- Focus: CLI-related test files
- Strategy: Update test expectations to match new CLI structure
- Target: <10 failing tests

### 🔄 **Phase 2: Integration Testing (Week 2)**
- End-to-end workflow testing (setup → hooks → run → report)
- Performance optimization for CLI startup times
- Documentation update for new CLI structure
- CI pipeline stabilization

### 📦 **Phase 3: Production Readiness (Week 3)**  
- License server integration testing
- Security audit of network calls and file permissions
- Package distribution testing
- User acceptance testing

---

## Next 5 Priority Tasks

1. **[CRITICAL]** Fix git hooks to use `--profile` instead of `--level` - *blocks commit/push workflows*
2. **[CRITICAL]** Add missing CLI subcommands (status, setup, doctor) - *breaks user expectations*  
3. **[HIGH]** Add `--level` argument to run command - *enables hook compatibility*
4. **[HIGH]** Skip license network calls when env vars missing - *prevents CLI hangs*
5. **[MEDIUM]** Fix failing CLI tests to stabilize CI pipeline - *blocks automated testing*

---

*Report generated on 2025-11-01 for FirstTry 0.5.0 (feat/ci-parity-mvp branch)*