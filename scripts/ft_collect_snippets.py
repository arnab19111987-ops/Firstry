#!/usr/bin/env python3
import json
import os
import re
import sys

# Collects exact code excerpts (line-numbered) for well-known helpers to embed as proof without modifying files.

TARGETS = [
    # Golden cache
    ("src/firsttry/ci_parity/cache_utils.py", r"(def\s+maybe_download_golden_cache\(.*\):[\s\S]*?)(?=\n\S|$)"),
    ("src/firsttry/ci_parity/cache_utils.py", r"(def\s+auto_refresh_golden_cache\(.*\):[\s\S]*?)(?=\n\S|$)"),
    # Divergence monitor
    ("src/firsttry/ci_parity/.*\.py", r"(exit\s*99|cache\s*escape|divergence)"),
    # License guard
    ("src/firsttry/.*license.*\.py", r"(def\s+check_.*license|class\s+License.*|LICENSE|KEY)"),
    # Telemetry toggle
    ("src/firsttry/.*", r"(telemetry|analytics|redact|PII|GDPR)")
]

def numbered(text):
    return "\n".join(f"{i+1:>6}: {line}" for i, line in enumerate(text.splitlines()))

def search_file(path, pattern):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
    except Exception:
        return None
    m = re.search(pattern, data, flags=re.MULTILINE)
    if not m: return None
    return numbered(m.group(0))

def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for root, _, files in os.walk("src"):
        for file in files:
            fp = os.path.join(root, file)
            for tpath, pat in TARGETS:
                # crude path match
                if re.fullmatch(tpath.replace(".", r"\.").replace("*", ".*"), fp):
                    snippet = search_file(fp, pat)
                    if snippet:
                        out = os.path.join(out_dir, os.path.basename(fp) + ".snippet.txt")
                        with open(out, "a", encoding="utf-8") as w:
                            w.write(f"== {fp} ==\n{snippet}\n\n")
                        results.append({"path": fp, "pattern": pat, "output": out})
    meta = {"count": len(results), "items": results}
    with open(os.path.join(out_dir, "snippets_index.json"), "w", encoding="utf-8") as w:
        json.dump(meta, w, indent=2)

if __name__ == "__main__":
    main()
