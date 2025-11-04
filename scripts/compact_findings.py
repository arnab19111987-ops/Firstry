#!/usr/bin/env python3
import json
import pathlib

for p in sorted(pathlib.Path('.firsttry').glob('*.json')):
    print(f"== {p.name} ==")
    d = json.loads(p.read_text())
    for c in d.get('checks', []):
        if c.get('status') != 'ok':
            s = c.get('summary') or c.get('message') or c.get('hint') or 'no-summary'
            print(f"{c.get('id')}\t{c.get('status')}\t{s[:200]}")
