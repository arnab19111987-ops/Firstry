## Local parity checks
## Local parity checks

Quick guide for developers to run the repo-adaptive CI parity checks locally.

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

