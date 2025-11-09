# FirstTry## Fast operational proof



> **Ship code that passes CI on the first try.**This repository includes a small demo tier (`free-fast`) that runs a known-clean

Python file and a tiny test so you can exercise cold→warm caching quickly.

[![CI](https://github.com/arnab19111987-ops/Firstry/workflows/CI/badge.svg)](https://github.com/arnab19111987-ops/Firstry/actions)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)Run the built Make helper to execute a cold then warm run and print the

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)report + history summary:



## Table of Contents```bash

make ft-proof

- [Overview](#overview)```

- [Features](#features)

- [Installation](#installation)Behavior:

- [Quick Start](#quick-start)- `free-fast` runs `ruff` on `src/ft_demo/math.py` (if present) and `pytest` on

- [Usage](#usage)	`tests/test_ok.py` (if present).

- [Configuration](#configuration)- The second run should show `cache_status: hit-local` for checks and exit `0`.

- [Performance](#performance)

- [Project Structure](#project-structure)If you want this demo enabled in CI, see `.github/workflows/firsttry-proof.yml`.

- [Development](#development)

- [Contributing](#contributing)## Telemetry (opt-out)

- [License](#license)

FirstTry sends **minimal, anonymized** usage metrics (e.g., command, tier, durations, success/fail) to help improve the tool.

## Overview- Endpoint: configurable via `FIRSTTRY_TELEMETRY_URL` (default internal endpoint)

- Stored locally: `.firsttry/telemetry_status.json`

FirstTry is a local CI engine that runs quality checks (linting, type checking, testing) on your codebase with intelligent caching and CI/CD workflow parity. Instead of discovering issues after pushing to remote CI, FirstTry validates your changes locally with the same checks that will run in CI, dramatically reducing fix-commit cycles.- **Opt-out**: set `FT_SEND_TELEMETRY=0`



**Problem:** Developers push code that fails CI, leading to:Examples:

- Slow feedback loops (minutes to discover issues)```bash

- Context switching between local development and remote failures# Disable telemetry for current shell

- Multiple commit-fix cycles that pollute git historyexport FT_SEND_TELEMETRY=0

- Team velocity drag from CI pipeline bottlenecks

# One-off run without telemetry

**Solution:** FirstTry provides:FT_SEND_TELEMETRY=0 python -m firsttry run

- **Sub-second feedback** for incremental changes via intelligent caching```

- **CI workflow parity** by parsing and executing the same steps as your GitHub Actions

- **Unified command interface** that replaces multiple manual tool invocations
- **Tier-based execution** from fast development loops to comprehensive validation

**Outcome:** Teams ship code that passes CI on the first try, eliminating the majority of pipeline failures and accelerating development velocity.

## Features

### Core Capabilities

- **🚀 Speed**: Intelligent file-hash caching with 287x performance improvements on warm runs
- **🔄 CI Parity**: Automatic CI workflow parsing and local execution of GitHub Actions steps
- **⚡ Smart Execution**: Changed-file detection with incremental validation
- **🎯 Tier-Based Workflows**: Fast dev loops to comprehensive pre-push validation
- **📊 Rich Reporting**: Detailed JSON reports with timing, cache status, and coverage metrics
- **🔒 Enterprise Ready**: License-gated features, S3 remote caching, audit trails

### Supported Tools & Languages

- **Python**: Ruff (linting), Black (formatting), MyPy (type checking), Pytest (testing)
- **Node.js**: ESLint, Prettier, npm/yarn/pnpm test suites
- **Security**: Bandit, secret scanning, dependency vulnerability checks
- **Quality Gates**: Coverage enforcement, pre-commit hooks, Docker smoke tests

### Workflow Integration

- **Git Hooks**: Automatic pre-commit and pre-push validation
- **GitHub Actions**: CI workflow mirroring and local execution
- **VS Code Extension**: IDE-integrated quality checking
- **Remote Caching**: S3-backed cache sharing across team members

## Installation

### Prerequisites

- Python 3.10 or higher
- Git repository with CI workflows (optional but recommended)

### Install from PyPI

```bash
pip install firsttry-run
```

### Local Development Install

```bash
git clone https://github.com/arnab19111987-ops/Firstry.git
cd Firstry
pip install -e ".[dev]"
```

### Verify Installation

```bash
ft doctor
```

## Quick Start

### 1. Initialize Project

```bash
# Navigate to your project directory
cd your-project

# Set up FirstTry configuration and hooks
ft setup
```

### 2. Run Quality Checks

```bash
# Fast development loop (Ruff only)
ft lite

# Standard development validation (Ruff + MyPy + Pytest)
ft ci

# Comprehensive pre-push validation
ft strict
```

### 3. View Results

```bash
# Show interactive dashboard of last run
ft dash

# View detailed JSON report
cat .firsttry/report.json
```

## Usage

### Command Reference

#### Fast Development Workflows

```bash
ft lite      # Ultra-fast linting (Ruff only)
ft ci        # CI-equivalent checks (Ruff + MyPy + Pytest)
ft strict    # Comprehensive validation
ft pro       # Professional tier features (requires license)
```

#### Tool-Specific Execution

```bash
ft ruff      # Python linting via FirstTry
ft mypy      # Type checking via FirstTry  
ft pytest    # Test execution via FirstTry
ft js-test   # JavaScript/TypeScript tests
```

#### Maintenance & Diagnostics

```bash
ft setup     # Install hooks, detect project configuration
ft doctor    # Diagnose environment and dependencies
ft status    # Show hook status and last run telemetry
```

#### Advanced Features

```bash
# Parse and display CI workflow steps
python -m firsttry mirror-ci

# Sync local config with CI workflows
python -m firsttry sync

# Run with specific options
python -m firsttry run ci --changed-only --show-report
```

### Execution Modes & Tiers

| Mode | Tier | Checks | Use Case |
|------|------|--------|----------|
| `lite` | free-lite | Ruff | Fast development iteration |
| `ci` / `strict` | free-strict | Ruff + MyPy + Pytest | Pre-push validation |
| `pro` | pro | Pro features | Team/enterprise usage |
| `enterprise` | promax | Full feature set | Large organizations |

### Common Flags

```bash
--changed-only    # Only check files modified since last commit
--no-cache       # Force fresh execution, bypass cache
--show-report    # Display detailed console output
--dry-run        # Preview execution plan without running
--interactive    # Show interactive menu after summary
```

## Configuration

### Basic Configuration (`.firsttry.yml`)

```yaml
# FirstTry configuration
gates:
  pre-commit:
    - lint
    - types
    - tests
  pre-push:
    - lint
    - types
    - tests
    - docker-smoke
```

### Advanced Configuration (`pyproject.toml`)

```toml
[tool.firsttry.coverage]
critical_min_rate = 60
critical_files = [
  "firsttry/state.py",
  "firsttry/smart_pytest.py", 
  "firsttry/planner.py",
  "firsttry/scanner.py",
]
```

### Environment Variables

```bash
# Disable telemetry
export FT_SEND_TELEMETRY=0

# Configure S3 remote caching (Enterprise)
export FT_S3_BUCKET=your-cache-bucket
export FT_S3_ENDPOINT=https://s3.amazonaws.com

# License key (Pro/Enterprise tiers)
export FIRSTTRY_LICENSE_KEY=your-license-key
```

## Performance

FirstTry's intelligent caching system provides significant performance improvements:

### Benchmark Results

```
Cold Run (first execution):  ~2-3s
Warm Run (cached results):   ~0.4s  
Cache Hit Rate:              95%+ for incremental changes
Speedup Factor:              287x on reference repository
```

### Performance Features

- **File-hash caching**: Only re-run checks on changed files
- **Stat-first validation**: Fast metadata checks before expensive hashing
- **Parallel execution**: Concurrent tool execution when possible
- **Smart invalidation**: Mutating tools properly invalidate downstream caches
- **Remote cache sharing**: S3-backed cache for team collaboration

## Project Structure

```
├── src/firsttry/           # Core FirstTry package
│   ├── cli.py             # Command-line interface
│   ├── cache/             # Caching infrastructure
│   ├── runners/           # Tool execution engines
│   ├── agents/            # CI parity and analysis agents
│   └── reporting/         # Output formatting and dashboards
├── tests/                 # Comprehensive test suite
│   ├── core/             # Core functionality tests
│   ├── enterprise/       # Enterprise feature tests
│   └── cache/            # Cache system tests
├── tools/                # Development and maintenance scripts
├── .github/workflows/    # CI/CD pipeline definitions
├── benchmarks/           # Performance testing utilities
└── docs/                 # Documentation and guides
```

### Key Components

- **CLI Layer**: Unified command interface with aliasing and help system
- **Execution Engine**: Parallel runner with caching and change detection
- **CI Parser**: GitHub Actions workflow analysis and local execution
- **Cache System**: Multi-tier caching with local and remote storage
- **Reporting**: Rich console output, JSON reports, and interactive dashboards

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run test suite
pytest tests/ -q

# Run with coverage
pytest tests/ --cov=src/firsttry --cov-report=term

# Run specific test categories
pytest tests/core/ -v           # Core functionality
pytest tests/enterprise/ -v    # Enterprise features
```

### Quality Checks

```bash
# Run all quality gates
make check

# Individual tools
ruff check .                   # Linting
black --check .               # Formatting
mypy .                        # Type checking

# Performance benchmarks
make perf
```

### Running Benchmarks

```bash
# Full benchmark suite
python benchmarks/bench_runner.py

# Performance validation
make ft-proof
```

## Contributing

We welcome contributions! Please see our contributing guidelines:

### Development Setup

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/Firstry.git`
3. Create a branch: `git checkout -b feature/your-feature`
4. Install development dependencies: `pip install -e ".[dev]"`
5. Make your changes and add tests
6. Run quality checks: `make check`
7. Submit a pull request

### Code Standards

- **Python 3.10+** compatibility required
- **Type hints** for all public APIs
- **Comprehensive tests** for new features
- **Performance considerations** for core execution paths
- **Documentation** updates for user-facing changes

### Testing Guidelines

- Write tests for both success and failure cases
- Include performance regression tests for optimization changes
- Test CI parity features against real workflow files
- Validate cache behavior with multiple execution scenarios

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

**FirstTry** • *CI/CD speed, without the cloud.*

For support, documentation, and updates, visit our [GitHub repository](https://github.com/arnab19111987-ops/Firstry).