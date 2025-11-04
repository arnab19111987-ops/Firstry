#!/usr/bin/env python3
"""
CI guard script: ensure repository invariants for concurrency and artifact policies.

Checks performed:
 - Exactly one asyncio.Semaphore(...) instantiation under src/firsttry
 - All run_cmd(...) callsites include a ctx= keyword (except the definition)
 - IGNORE_DIRS or IGNORE_GLOBS only appear in allowed files (ignore.py, checks/bandit_sharded.py)

Exit code: 0 if all checks pass, non-zero otherwise. Prints helpful diagnostics.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "firsttry"

def files_under_src():
    for p in SRC.rglob("*.py"):
        yield p

def count_asyncio_semaphores():
    pattern = re.compile(r"asyncio\.Semaphore\s*\(")
    cnt = 0
    locations = []
    for f in files_under_src():
        s = f.read_text(encoding='utf-8')
        for m in pattern.finditer(s):
            cnt += 1
            # compute line number
            ln = s[: m.start()].count("\n") + 1
            locations.append((f.relative_to(ROOT), ln))
    return cnt, locations

def find_run_cmd_without_ctx():
    # Find occurrences of run_cmd( (but not _run_cmd) that do not include ctx= inside the call
    bad = []
    pattern = re.compile(r"(?<!_)\brun_cmd\s*\(")
    for f in files_under_src():
        s = f.read_text(encoding='utf-8')
        lines = s.splitlines()
        for i, line in enumerate(lines):
            if pattern.search(line) and not line.lstrip().startswith(('def ', 'async def ')):
                # capture snippet: this line + next 3 lines
                snippet = '\n'.join(lines[i : i + 4])
                if 'ctx=' not in snippet:
                    bad.append((f.relative_to(ROOT), i + 1, snippet.strip()))
    return bad

def find_ignore_constant_misuse():
    allowed = {Path('src/firsttry/ignore.py'), Path('src/firsttry/checks/bandit_sharded.py')}
    bad = []
    pattern = re.compile(r"IGNORE_(DIRS|GLOBS)")
    for f in files_under_src():
        rel = f.relative_to(ROOT)
        s = f.read_text(encoding='utf-8')
        if pattern.search(s) and rel not in allowed:
            ln = s[: pattern.search(s).start()].count('\n') + 1
            bad.append((rel, ln))
    return bad

def main():
    ok = True

    sem_cnt, sem_locs = count_asyncio_semaphores()
    if sem_cnt != 1:
        print(f"ERROR: expected exactly 1 asyncio.Semaphore(...) in src/firsttry but found {sem_cnt}")
        for loc in sem_locs:
            print(f"  - {loc[0]}:{loc[1]}")
        ok = False
    else:
        print(f"OK: found one asyncio.Semaphore at {sem_locs[0][0]}:{sem_locs[0][1]}")

    bad_run_cmd = find_run_cmd_without_ctx()
    if bad_run_cmd:
        print("ERROR: found run_cmd(...) callsites that do not include ctx= (within 3 lines):")
        for rel, ln, snippet in bad_run_cmd:
            print(f"  - {rel}:{ln}: {snippet}")
        ok = False
    else:
        print("OK: all run_cmd(...) callsites include ctx= (or are definitions)")

    bad_ignores = find_ignore_constant_misuse()
    if bad_ignores:
        print("ERROR: IGNORE_DIRS/IGNORE_GLOBS found outside allowed files:")
        for rel, ln in bad_ignores:
            print(f"  - {rel}:{ln}")
        ok = False
    else:
        print("OK: IGNORE constants only appear in allowed files")

    if not ok:
        sys.exit(2)

if __name__ == '__main__':
    main()
