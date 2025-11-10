# Gate Registry & Configuration Guide

This document is automatically generated from the FirstTry codebase.
It provides a complete reference of all available gates and their configurations.

## Available Gates

| Gate ID | Module | Description | Class |
|---------|--------|-------------|-------|
| `ci_files_changed` | `src/firsttry/gates/ci_files_changed.py` | Gate that checks if CI files have changed | `CiFilesChangedGate` |
| `config_drift` | `src/firsttry/gates/config_drift.py` | Gate that checks for configuration drift | `ConfigDriftGate` |
| `coverage_check` | `src/firsttry/gates/coverage_check.py` | Gate that checks code coverage | `CoverageCheckGate` |
| `deps_lock` | `src/firsttry/gates/deps_lock.py` | Gate that checks for dependency lock files | `DepsLockGate` |
| `drift_check` | `src/firsttry/gates/drift_check.py` | Gate that checks for configuration drift | `DriftCheckGate` |
| `env_tools` | `src/firsttry/gates/env_tools.py` | Gate that checks environment tools | `EnvToolsGate` |
| `go_tests` | `src/firsttry/gates/go_tests.py` | Gate that runs Go tests | `GoTestGate` |
| `node_tests` | `src/firsttry/gates/node_tests.py` | Gate that runs npm tests for Node.js projects | `NodeNpmTestGate` |
| `precommit_all` | `src/firsttry/gates/precommit_all.py` | Gate that runs all pre-commit checks | `PreCommitAllGate` |
| `python_lint` | `src/firsttry/gates/python_lint.py` | Gate that runs ruff linting on Python code | `PythonRuffGate` |
| `python_mypy` | `src/firsttry/gates/python_mypy.py` | Gate that runs mypy type checking on Python code | `PythonMypyGate` |
| `python_pytest` | `src/firsttry/gates/python_pytest.py` | Gate that runs pytest tests on Python code | `PythonPytestGate` |
| `security_bandit` | `src/firsttry/gates/security_bandit.py` | Gate that runs bandit security scanning on Python code | `SecurityBanditGate` |

## Gate Descriptions

### `ci_files_changed` - CiFilesChangedGate

**Module:** `src/firsttry/gates/ci_files_changed.py`
**Description:** Gate that checks if CI files have changed

**Details:**

Gate that checks if CI files have changed.

### `config_drift` - ConfigDriftGate

**Module:** `src/firsttry/gates/config_drift.py`
**Description:** Gate that checks for configuration drift

**Details:**

Gate that checks for configuration drift.

### `coverage_check` - CoverageCheckGate

**Module:** `src/firsttry/gates/coverage_check.py`
**Description:** Gate that checks code coverage

**Details:**

Gate that checks code coverage.

### `deps_lock` - DepsLockGate

**Module:** `src/firsttry/gates/deps_lock.py`
**Description:** Gate that checks for dependency lock files

**Details:**

Gate that checks for dependency lock files.

### `drift_check` - DriftCheckGate

**Module:** `src/firsttry/gates/drift_check.py`
**Description:** Gate that checks for configuration drift

**Details:**

Gate that checks for configuration drift.

### `env_tools` - EnvToolsGate

**Module:** `src/firsttry/gates/env_tools.py`
**Description:** Gate that checks environment tools

**Details:**

Gate that checks environment tools.

### `go_tests` - GoTestGate

**Module:** `src/firsttry/gates/go_tests.py`
**Description:** Gate that runs Go tests

**Details:**

Gate that runs Go tests.

### `node_tests` - NodeNpmTestGate

**Module:** `src/firsttry/gates/node_tests.py`
**Description:** Gate that runs npm tests for Node.js projects

**Details:**

Gate that runs npm tests for Node.js projects.

### `precommit_all` - PreCommitAllGate

**Module:** `src/firsttry/gates/precommit_all.py`
**Description:** Gate that runs all pre-commit checks

**Details:**

Gate that runs all pre-commit checks.

### `python_lint` - PythonRuffGate

**Module:** `src/firsttry/gates/python_lint.py`
**Description:** Gate that runs ruff linting on Python code

**Details:**

Gate that runs ruff linting on Python code.

### `python_mypy` - PythonMypyGate

**Module:** `src/firsttry/gates/python_mypy.py`
**Description:** Gate that runs mypy type checking on Python code

**Details:**

Gate that runs mypy type checking on Python code.

### `python_pytest` - PythonPytestGate

**Module:** `src/firsttry/gates/python_pytest.py`
**Description:** Gate that runs pytest tests on Python code

**Details:**

Gate that runs pytest tests on Python code.

### `security_bandit` - SecurityBanditGate

**Module:** `src/firsttry/gates/security_bandit.py`
**Description:** Gate that runs bandit security scanning on Python code

**Details:**

Gate that runs bandit security scanning on Python code.

## Usage Examples

### Basic Configuration

```yaml
# .firsttry.yml
gates:
  pre-commit:
    - ci_files_changed
    - config_drift
    - coverage_check
    - deps_lock
    - drift_check
  pre-push:
    - lint
    - types
    - tests
```

### Command Line Usage

```bash
# Run specific gate
firsttry run --gate ci_files_changed

# Run multiple gates
firsttry run --gate pre-commit

# List available gates
firsttry gates
```

---

*Documentation generated automatically from 13 gate classes*
*Last updated: /workspaces/Firstry/scripts/generate_gates_doc.py inspection*
