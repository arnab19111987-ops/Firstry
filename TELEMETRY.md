# Telemetry

This document describes FirstTry's telemetry behavior (implementation is in `src/firsttry/telemetry.py`).

Summary

- FirstTry includes a minimal, best-effort telemetry sender intended to help the maintainers improve the tool.
- Telemetry is opt-in by default in code; it will only send data if explicitly enabled.

What is sent (high-level)

Based on `src/firsttry/telemetry.py`, telemetry payloads include a small summary of a run, for example:

- `schema_version` (telemetry schema version)
- `tier` and `profile` (which tier/profile was executed)
- `timing` (durations / timing metrics)
- `checks` array: for each check, an object with `id`, `status`, and `locked` flag

The implementation serializes only these structured fields; it does not package or transmit repository source files.

Control / environment variables

- `FIRSTTRY_SEND_TELEMETRY` (strict opt-in): set to `1` / `true` / `yes` to enable telemetry.
- `FIRSTTRY_TELEMETRY_OPTOUT`: set to `1` / `true` / `yes` to force opt-out (hard opt-out).
- `DO_NOT_TRACK`: alternate opt-out environment variable (compatible values: `1`, `true`, `yes`).
- `FIRSTTRY_TELEMETRY_URL`: override the telemetry endpoint (defaults to the built-in URL in code).

Local status

- The telemetry writer records a local status file at `.firsttry/telemetry_status.json` with the last send status and timestamp.
- The CLI provides a `doctor` / `status` check that can report the telemetry status from that file.

Privacy and data limits

- The code records high-level run metadata, durations, and check IDs/statuses.
- It does not read or transmit repository source code files, test file contents, or secrets (there is no code that collects or sends raw file contents or environment variable values).
- Network errors and submission status are recorded locally in `.firsttry/telemetry_status.json`.

Recommendations for users

- If you do not want to participate in telemetry, set one of the opt-out variables:

```bash
export FIRSTTRY_TELEMETRY_OPTOUT=1
# or
export DO_NOT_TRACK=1
```

- To explicitly enable telemetry (opt-in):

```bash
export FIRSTTRY_SEND_TELEMETRY=1
```

- To change where telemetry is sent (for local testing or internal collection):

```bash
export FIRSTTRY_TELEMETRY_URL=https://your.internal/telemetry/collect
```

If you need a stronger guarantee or a full data schema, please inspect `src/firsttry/telemetry.py` for the exact payload construction.
