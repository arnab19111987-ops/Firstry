#!/usr/bin/env python3
"""Remove leading/trailing Markdown code fences from test files.

Scans for files under `tests/`, `licensing/tests/`, and `tools/**/tests/`.
If a file starts with a line that begins with ``` and ends with ``` then the
script removes the first and last such fence lines.
"""
import pathlib

root = pathlib.Path.cwd()
patterns = ["tests/**/*.py", "licensing/**/*.py", "tools/**/tests/**/*.py"]
count = 0
for pat in patterns:
    for p in root.glob(pat):
        try:
            s = p.read_text(encoding="utf-8")
        except Exception:
            continue
        lines = s.splitlines()
        if (
            len(lines) >= 2
            and lines[0].strip().startswith("```")
            and lines[-1].strip().startswith("```")
        ):
            # remove first and last fence lines
            new = "\n".join(lines[1:-1]) + "\n"
            p.write_text(new, encoding="utf-8")
            count += 1
print(f"Fixed {count} files")
