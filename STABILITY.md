# Stability & CI Rules

This document records the stability rules and practices introduced to keep the
FirstTry repo predictable and to detect regressions before they affect users.

Key rules

- **`.firsttry/**` is generated and ignored.**
  - Files under `.firsttry/` are generated artifacts (snapshots, audit logs, caches).
  - They are not source and must not cause tests to fail. Tests that scan the tree
    should explicitly ignore `.firsttry/**` rather than relying on vague patterns.

- **`FIRSTTRY_SHARED_SECRET` test fixture behavior.**
  - Tests rely on a deterministic shared secret in dev/test runs. We provide an
    autouse pytest fixture in `tests/conftest.py` that sets a dev-only fallback
    when the environment variable is missing. The fixture only sets the value
    if it is not already present — it does not override a real secret.

- **Parity lock rule (pyproject.toml ↔ `ci/parity.lock.json`).**
  - `ci/parity.lock.json` must reference the active `pyproject.toml` sha256 (or a
    matching prefix). If you change `pyproject.toml`, update the lock entry.
  - To refresh the hash: run `sha256sum pyproject.toml` and update
    `ci/parity.lock.json` accordingly. We also add a test
    `tests/ci/test_parity_lock_matches_pyproject.py` to enforce this.

- **Pre-commit hook contract.**
  - The project uses a pre-commit parity gate. Locally the hook runs with
    `GIT_HOOK=pre-push FT_NO_NETWORK=1 python -m firsttry.cli pre-commit`.
  - CI should run the same contract to ensure parity between developer machines
    and the build environment.

- **Test & merge rules.**
  - No public change without tests: any behavioral change must include tests.
  - The test suite is sacred: green test suite is required before merge. CI will
    run the gate checks (ruff, pytest gate, pre-commit parity) and merges will
    be blocked unless they pass.

Using the stability script

- `tools/test_ft_run_stability.sh` is a convenience script to run `ft run` 30
  times locally to detect non-determinism or intermittent tracebacks. Run it
  when changing CLI/planner/runtime code locally before pushing.

Nightly checks

- Consider wiring `tools/test_ft_run_stability.sh` into a nightly CI job so
  we detect flaky regressions early without slowing every push.

CLI surface contracts (Dev tier)

We freeze and document the Dev CLI surface so that developers and users have a
stable, narrow, and easy-to-use experience. For the Dev tier the CLI shall
expose the following commands and semantics:

- `ft run`
  - The one boring, obvious entrypoint. Runs the default pipeline for the
    developer's workspace. Should be deterministic and stable across repeated
    runs (use `tools/test_ft_run_stability.sh` to validate changes).

- `ft init`
  - Initialize a workspace with sensible defaults for development. Should be
    idempotent and non-destructive.

- `ft pre-commit`
  - Run the local pre-commit parity gate. Uses `GIT_HOOK=pre-push` semantics when
    appropriate.

- `ft cache clear`
  - Clear local caches used by the CLI. Should be safe to run anytime.

- `ft parity` (warn-only)
  - Run parity checks but do not block local development by default; meant for
    diagnostic usage. CI will still enforce parity strictly.

Rules

- Hide or remove complexity related to tiers, licenses, enterprise-only parity
  enforcement, golden cache PRO features, or anything that dilutes the Dev
  surface. If a feature is enterprise-only, keep it out of the Dev CLI surface
  and document it separately under an `enterprise/` or `docs/` area.

- Update tests whenever you modify CLI contracts. The STABILITY checks and the
  nightly stability job will help detect regressions, but unit/integration
  tests are the primary contract for behavior.
