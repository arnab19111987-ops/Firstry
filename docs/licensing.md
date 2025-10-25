# FirstTry Licensing Model

## Environment variables

- `FIRSTTRY_LICENSE_KEY`
  - A string provided after purchase.
  - Must be present to unlock Pro features such as `mirror-ci --run`.

- `FIRSTTRY_LICENSE_URL`
  - Base URL of the license verification service.
  - Used by the CLI to validate the key.
  - Not required for offline cached mode.

## CLI behavior

### Free mode
- You can run:
  - `firsttry run --gate <...>`
  - `firsttry doctor`
  - `firsttry mirror-ci` (dry-run only, no `--run`)
  - `firsttry install-hooks`

### Pro mode
- Requires `FIRSTTRY_LICENSE_KEY`.
- Unlocks:
  - `firsttry mirror-ci --run`  
    This executes the mapped CI steps locally so you catch failures *before* pushing.
- The CLI will refuse `--run` if there is no license.

### Offline / cache
- After a successful license check, the CLI stores a short-lived cache file locally
  (e.g. `~/.firsttry/license.json`).
- If you are offline, FirstTry will attempt to use the cached validation for a grace period.
- If the cache is missing or expired, Pro features may degrade (you'll still get dry-run).

## Failure modes
- If validation fails or no key is present:
  - Pro-only commands return a structured JSON summary:
    ```json
    {
      "ok": false,
      "results": [
        {
          "job": "license-check",
          "step": "validate-license",
          "returncode": 1,
          "output": "License validation failed: <reason>"
        }
      ]
    }
    ```
  - The CLI exits with code 1.

## Support expectations
- We guarantee that:
  - `firsttry mirror-ci --run` will execute steps from your repo's GitHub Actions
    and match them locally **before you push**.
  - We will not run destructive commands on your machine.
  - You will see which step failed and why.

- We do NOT guarantee:
  - 100% parity with cloud resources (self-hosted runners, secrets, etc.).
  - Support for every custom action in the GitHub marketplace.
