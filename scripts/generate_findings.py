#!/usr/bin/env python3
import json
import pathlib

out = ["# FirstTry Findings (current repo)\n"]
for p in sorted(pathlib.Path('.firsttry').glob('*.json')):
    d = json.loads(p.read_text())
    bad = [c for c in d.get('checks', []) if c.get('status') != 'ok']
    out.append(f"## {p.name}\n" + ("✅ No issues\n" if not bad else ""))
    for c in bad:
        summary = c.get('summary') or c.get('message') or c.get('hint') or 'no-summary'
        out.append(f"- **{c.get('id')}** — `{c.get('status')}`: {summary}")

pathlib.Path('.firsttry/FIRSTTRY_FINDINGS.md').write_text('\n'.join(out))
print('Wrote .firsttry/FIRSTTRY_FINDINGS.md')
