CLI compatibility
-----------------

Current Truth vs Plan:

- Current Truth: the CLI is implemented using `argparse` in `src/firsttry/cli.py` (see `build_parser()` / `main()`).
- Planned: a future migration to Click is noted in docs; the code currently uses argparse.

This repository provides a small CLI under `firsttry`.

- For backward-compatibility with some older tests, `firsttry/cli.py` also exposes `build_parser()` and argparse-compatible wrappers that return integer exit codes.

How to run

- How to run (argparse):

```bash
python -m firsttry run --gate pre-commit
python -m firsttry mirror-ci --root .
```

Argparse wrapper (programmatic/tests):

```python
from firsttry.cli import build_parser
parser = build_parser()
ns = parser.parse_args(["run", "--gate", "pre-commit"])
# Use `firsttry.main()` to execute the parsed args in tests
rc = firsttry.cli.main(ns)
```

Notes

- Tests may monkeypatch `firsttry.cli.runners` and `firsttry.cli.assert_license` to avoid executing external commands.
- The Click-based CLI is the recommended interactive entrypoint; the argparse functions are maintained for compatibility.

Enabling real runners (optional)

If you want the CLI to use the real `tools/firsttry` runners implementation instead of the safe stubs, set the environment variable
`FIRSTTRY_USE_REAL_RUNNERS` before importing or invoking the CLI. Example:

```bash
FIRSTTRY_USE_REAL_RUNNERS=1 python -m firsttry run --gate pre-commit
```

Behavior and caveats:

- When `FIRSTTRY_USE_REAL_RUNNERS` is truthy (1/true/yes) and a `tools/firsttry/firsttry/runners.py` file exists, the CLI will attempt to dynamically import that module and use its callables (e.g. `run_ruff`).
- If the import fails or the module doesn't provide a callable, the CLI logs the error and falls back to the safe stubs. This ensures hooks or CI won't crash unexpectedly.
- The real `tools/firsttry` runners module may have import-time side effects (dataclasses/packaging context issues were observed in some environments). Only enable the flag when you know the runtime environment matches the expectations of that module (same package layout / PYTHONPATH).
- If you need to load runners from a different location, I can add a `FIRSTTRY_RUNNERS_MODULE` option to configure an import path instead of the default file location.

The safe stubs still log a DEBUG message when used, so it's easy to detect whether the real runners were invoked in logs.
