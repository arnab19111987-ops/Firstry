## Local parity checks

Quick guide for developers to run the repo-adaptive CI parity checks locally.

### Auto-Bootstrap (Recommended)

**The parity environment sets up automatically on first `ft` command run!**

When you run any `ft` command in a Git repository with `ci/parity.lock.json`, FirstTry will:
1. Create `.venv-parity` environment (if needed)
2. Install all parity tools (ruff, mypy, pytest, bandit)
3. Install Git hooks for automatic checking (pre-commit + pre-push)

**No manual setup required!** Just run:

```bash
ft --version   # Triggers auto-bootstrap on first run
```

**Opt-out (for end-users or custom CI):**

```bash
export FIRSTTRY_DISABLE_AUTO_PARITY=1
ft --version   # Skips auto-bootstrap
```

The auto-bootstrap only affects **developer repositories** with `ci/parity.lock.json`. End-user installations are never affected.

### Git Hooks (Installed Automatically)

After auto-bootstrap, Git will automatically run parity checks:

- **pre-commit**: Fast self-check (`--self-check --explain`)
  - Validates config hashes, tool versions, test collection
  - Runs in seconds
  - Blocks commits if parity is broken

- **pre-push**: Full parity check (`--parity --explain`)
  - Runs all checks: linting, types, tests, coverage, security
  - Network sandboxed (FT_NO_NETWORK=1)
  - Blocks pushes if quality gates fail

**Manual hook installation** (if needed):

```bash
python -m firsttry.ci_parity.install_hooks
```

### Manual Parity Commands

- Install the pre-commit hook that ensures the runner is used where configured:

```bash
pre-commit install
```

- Run local CI-parity checks (profiles):

  - Commit profile (fast):

    ```bash
    python -m firsttry.ci_parity.runner pre-commit
    ```

  - Push profile (broader):

    ```bash
    python -m firsttry.ci_parity.runner pre-push
    ```

  - CI profile (full):

    ```bash
    python -m firsttry.ci_parity.runner ci
    ```

- Dry-run any profile (shows planned commands only):

```bash
FT_CI_PARITY_DRYRUN=1 python -m firsttry.ci_parity.runner <profile>
```

Optional per-repo overrides: create `firsttry.toml` with:

```toml
[firsttry.profiles.commit]
include = ["black", "ruff", "mypy", "pytest"]

[firsttry.env]
# If your repo layout doesn't use `src/`, override PYTHONPATH for runner
# PYTHONPATH = "."
```

Quick shortcuts (copy-paste):

```bash
make hooks-install    # install the repo pre-push hook that calls the runner
make ft-pre-commit    # shows pre-commit plan (dry-run)
make ft-pre-push      # shows pre-push plan (dry-run)
make ft-ci            # shows ci plan (dry-run)
# To run for real: unset FT_CI_PARITY_DRYRUN and re-run the same commands
```

Sanity cross-checks
-------------------

Run these locally to validate the parity tooling quickly.

```bash
# Unit tests for the parity layer
PYTHONPATH=src pytest -q tests/ci_parity

# Dry-run runner profiles (print plan only)
FT_CI_PARITY_DRYRUN=1 PYTHONPATH=src python -m firsttry.ci_parity.runner pre-commit
FT_CI_PARITY_DRYRUN=1 PYTHONPATH=src python -m firsttry.ci_parity.runner pre-push
FT_CI_PARITY_DRYRUN=1 PYTHONPATH=src python -m firsttry.ci_parity.runner ci
```

