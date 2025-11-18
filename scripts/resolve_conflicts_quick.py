#!/usr/bin/env python3
"""Quick conflict resolver: for each target file, if it contains git conflict markers,
keep the LOWER variant (the section between '=======' and '>>>>>>>') when present.
This is a heuristic quick-fix for merge artifacts; always review changes before pushing.
"""
from pathlib import Path

FILES = [
    ".githooks/pre-commit",
    ".githooks/pre-push",
    ".firsttry/Dockerfile",
    ".firsttry/ci-extra-requirements.txt",
    ".firsttry/history.jsonl",
    ".github/workflows/firsttry-ci-parity.yml",
    ".pre-commit-config.yaml",
    "Makefile",
    "tests/ci_parity/test_planner_mypy_config_detection.py",
    "tests/test_no_alias_in_repo.py",
]


def main() -> None:
    cwd = Path(".").resolve()
    changed: list[str] = []

    for fname in FILES:
        p = cwd / fname
        if not p.exists():
            print(f"SKIP (missing): {fname}")
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if "<<<<<<<" not in txt:
            print(f"CLEAN: {fname} (no markers)")
            continue

        out_lines: list[str] = []
        i = 0
        lines = txt.splitlines()
        n = len(lines)
        while i < n:
            line = lines[i]
            if line.startswith("<<<<<<<"):
                # skip to =======, then take lower section until >>>>>>>
                i += 1
                top: list[str] = []
                while i < n and not lines[i].startswith("======="):
                    top.append(lines[i])
                    i += 1
                if i < n and lines[i].startswith("======="):
                    i += 1
                bottom: list[str] = []
                while i < n and not lines[i].startswith(">>>>>>>"):
                    bottom.append(lines[i])
                    i += 1
                # skip the >>>>>>> line
                if i < n and lines[i].startswith(">>>>>>>"):
                    i += 1
                # prefer bottom if non-empty, else top
                if any(ln.strip() for ln in bottom):
                    out_lines.extend(bottom)
                else:
                    out_lines.extend(top)
            else:
                out_lines.append(line)
                i += 1

        newtxt = "\n".join(out_lines) + "\n"
        bak = p.with_suffix(p.suffix + ".bak") if p.suffix else Path(str(p) + ".bak")
        try:
            p.rename(bak)
        except Exception:
            # if rename fails (maybe file in use), write backup separately
            (p.parent / (p.name + ".bak")).write_text(txt, encoding="utf-8")
        p.write_text(newtxt, encoding="utf-8")
        changed.append(fname)
        print(f"FIXED: {fname} -> kept lower variant where present; backup saved")

    print("\nSUMMARY:")
    print(f"Processed {len(FILES)} files, changed {len(changed)} files")
    if changed:
        print("\nChanged files:")
        for c in changed:
            print(" -", c)


if __name__ == "__main__":
    main()
