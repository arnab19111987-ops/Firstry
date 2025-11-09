#!/usr/bin/env python3
import json
import sys
from pathlib import Path

CRITICAL = [
    "firsttry/state.py",
    "firsttry/smart_pytest.py",
    "firsttry/planner.py",
    "firsttry/scanner.py",
]


def read_coverage(path="coverage.json"):
    p = Path(path)
    if not p.exists():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    files = d.get("files") or {}
    out = {}
    for k, v in files.items():
        kk = k.replace("\\", "/")
        out[kk] = v.get("summary", {}).get("percent_covered")
    return out


def augment_audit(audit_path=".firsttry/audit/AUDIT_REPORT.json", cov_path="coverage.json"):
    cov = read_coverage(cov_path)
    p = Path(audit_path)
    if not p.exists():
        print(f"Audit not found: {p}", file=sys.stderr)
        return 1
    audit = json.loads(p.read_text(encoding="utf-8"))
    audit.setdefault("evidence", {})
    audit["evidence"]["coverage_critical"] = {
        f: cov.get(next((k for k in cov if k.endswith(f)), "missing"), None) for f in CRITICAL
    }
    p.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Embedded critical coverage into audit JSON.")
    return 0


if __name__ == "__main__":
    sys.exit(augment_audit(*sys.argv[1:]))
