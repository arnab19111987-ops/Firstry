# FirstTry

**Pass CI on the first try.**

FirstTry is a pre-commit quality gate that runs the same checks your CI does, locally, before you push. No more "fix lint" commits.

<!-- ci-trigger: touch to run CI workflows -->

## Quick Start

```bash
# Install
pip install firsttry

# Run checks before commit
firsttry run --gate pre-commit

# Install git hooks for automatic checking
firsttry install-hooks

# See what your CI will run
firsttry mirror-ci --root .
```

## Features

### 🚀 Pre-Commit/Pre-Push Gates

Run quality checks before commits hit CI:

```bash
firsttry run --gate pre-commit
```

**Output:**
```
FirstTry Gate Summary
---------------------
Lint.......... PASS ruff
Format........ PASS black-check
Types......... PASS mypy
Tests......... PASS pytest
Coverage XML.. PASS coverage_xml
Coverage Gate. PASS coverage_gate

Verdict: SAFE TO COMMIT ✅

Everything looks good. You'll almost certainly pass CI on the first try.
```

### 🔍 Mirror CI Locally

See exactly what your GitHub Actions workflows will run:

```bash
firsttry mirror-ci --root .
```

**Example Output:**
```
Workflow: ci.yml
  Job: qa
    Step: Lint
      Run:
        ruff check .
    Step: Test
      Run:
        pytest -q
    Step: Type Check
      Run:
        mypy .
```

This is your CI plan as a dry-run checklist.

### ⚙️ Environment Variables

#### `FIRSTTRY_USE_REAL_RUNNERS`

Toggle between stub runners (fast, no dependencies) and real analysis tools:

```bash
# Use lightweight stubs (default)
firsttry run --gate pre-commit

# Use real ruff, black, mypy, pytest
FIRSTTRY_USE_REAL_RUNNERS=1 firsttry run --gate pre-commit
```

**Why this matters:**
- Stubs: Fast feedback loop during development
- Real runners: Serious analysis before pushing
- **One env var to flip** between "quick sanity" and "CI-grade checks"

Perfect for CI pipelines, pre-push hooks, or when you want confidence.

## Installation

```bash
pip install firsttry
```

Or from source:

```bash
git clone https://github.com/arnab19111987-ops/Firstry.git
cd Firstry
pip install -e .
```

## Commands

### `firsttry run`

Run a quality gate (pre-commit or pre-push).

```bash
firsttry run --gate pre-commit
firsttry run --gate pre-push
firsttry run --gate pre-commit --require-license
```

**Options:**
- `--gate`: Which gate to run (`pre-commit` | `pre-push`)
- `--require-license`: Fail if license check fails

### `firsttry install-hooks`

Install git hooks that automatically run FirstTry before commits/pushes.

```bash
firsttry install-hooks
```

Creates:
- `.git/hooks/pre-commit` - Runs `pre-commit` gate
- `.git/hooks/pre-push` - Runs `pre-push` gate

### `firsttry mirror-ci`

Show what CI workflows will run, locally.

```bash
firsttry mirror-ci --root .
```

**Options:**
- `--root`: Project root containing `.github/workflows` (default: `.`)

## Runners API (Semi-Stable)

FirstTry's runner interface is **semi-stable**. You can build alternate runner packs by implementing:

```python
from types import SimpleNamespace

def run_ruff(args) -> SimpleNamespace:
    """Run ruff linter."""
    return SimpleNamespace(
        ok=True,           # bool: did the check pass?
        name="ruff",       # str: runner name
        duration_s=0.5,    # float: how long it took
        stdout="",         # str: command stdout
        stderr="",         # str: command stderr
        cmd=("ruff", ...") # tuple: command that ran
    )

def run_black_check(args) -> SimpleNamespace:
    """Run black formatter check."""
    # Same signature as above

def run_mypy(args) -> SimpleNamespace:
    """Run mypy type checker."""
    # Same signature as above
```

**Why you'd want this:**
- Ship alternate tool sets (ruff → pylint, black → yapf)
- Add company-specific checks
- Integrate proprietary analysis tools

Place your runners in `tools/firsttry/firsttry/runners.py` and set `FIRSTTRY_USE_REAL_RUNNERS=1`.

## Development

```bash
# Run tests
pytest -q

# Run with real runners
FIRSTTRY_USE_REAL_RUNNERS=1 pytest -q

# Install in editable mode
pip install -e .
```

## License

MIT

## Tags & Branches

- `firsttry-core-v0.1`: First stable release, 42/42 tests passing, hardened runner loader
- `feat/firsttry-stable-core`: Development branch for stable core features
