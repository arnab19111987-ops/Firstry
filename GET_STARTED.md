# Get Started with FirstTry (Public Beta)

Welcome! This guide helps you try FirstTry locally and via the optional VS Code extension.

What FirstTry does for you

- Before you push, FirstTry runs ruff, mypy, pytest, and a coverage gate (80%).
- It also performs CI workflow parsing and lightweight probes so the checks you run locally match what CI will run.
- Goal: your PR goes green on first push — fewer fix-commit cycles.

Quickstart (60 seconds)

1. clone repo

```bash
git clone https://github.com/arnab19111987-ops/Firstry.git
cd Firstry
```

2. install dev deps

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
# optional: pin dev tool versions
if [ -f requirements-dev.txt ]; then
  pip install -r requirements-dev.txt
fi
```

3. run the full gate locally

```bash
make check
```

### Check your toolchain

You can quickly verify essential external tools are available locally:

```bash
ft doctor --tools
# nonzero exit if something critical is missing
```

### Perf snapshot

Capture a small, versioned snapshot of local perf & reports:

```bash
make perf
# logs at benchmarks/ft_logs/
```

Install the VSIX (optional)

1. Download the latest `firsttry-extension-0.0.1.vsix` from the v0.1.0-beta release: https://github.com/arnab19111987-ops/Firstry/releases/tag/v0.1.0-beta
2. In VS Code: Extensions panel → `...` menu → "Install from VSIX..." → select the file
3. After install, run the command: "FirstTry: Run Pre-Commit Gate"
4. Fix anything red. Commit only when it's green.

What 'red' means

- Ruff fails: code style problems (autoformat or fix as suggested).
- Mypy fails: type inconsistencies — fix function signatures and types.
- Pytest fails: failing tests — fix the underlying bug or the test.
- Coverage < 80%: add tests for product-facing behaviors.
- Workflow parsing fails: your .github/workflows may have unusual/unsupported constructs.

Selling line

This is the same bar applied in CI. If you’re green here, you’ll be green on GitHub.
