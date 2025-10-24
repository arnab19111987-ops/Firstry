CLI compatibility
-----------------

This repository provides a small CLI under `firsttry`.

- The modern entrypoint uses Click and is implemented in `firsttry/cli.py` as a `click.Group` named `main`.
- For backward-compatibility with some older tests, `firsttry/cli.py` also exposes `build_parser()` and argparse-compatible wrappers that return integer exit codes.

How to run

- Click (recommended):

```bash
python -m firsttry run --gate pre-commit
python -m firsttry mirror-ci --root .
```

- Argparse wrapper (programmatic/tests):

```python
from firsttry.cli import build_parser
parser = build_parser()
ns = parser.parse_args(["run", "--gate", "pre-commit"])
rc = ns.func(ns)
```

Notes

- Tests may monkeypatch `firsttry.cli.runners` and `firsttry.cli.assert_license` to avoid executing external commands.
- The Click-based CLI is the recommended interactive entrypoint; the argparse functions are maintained for compatibility.
