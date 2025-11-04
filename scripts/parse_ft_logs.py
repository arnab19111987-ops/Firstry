#!/usr/bin/env python3
import re
from pathlib import Path

dirp = Path('benchmarks/ft_cmd_logs')
out = []
for p in sorted(dirp.glob('*.log')):
    txt = p.read_text()
    # Find exit/rc lines? Not present in many logs; extract patterns
    errors = []
    for line in txt.splitlines():
        if re.search(r'(?i)error|traceback|exception|failed|❌|locked|missing|KeyboardInterrupt', line):
            errors.append(line.strip())
    # Take the first 6 lines as preview
    preview = '\n'.join(txt.splitlines()[:6])
    out.append(f"## {p.name}\n\nPREVIEW:\n{preview}\n\nKEYS:\n" + (('\n'.join(errors) if errors else 'No key errors found') ) + "\n\n---\n")

report = '\n'.join(out)
Path('benchmarks/ft_cmd_logs/COMMAND_SUMMARY.md').write_text(report)
print('Wrote benchmarks/ft_cmd_logs/COMMAND_SUMMARY.md')
