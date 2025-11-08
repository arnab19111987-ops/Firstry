#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

# Import the emitter
from tools.audit_emit import emit_audit_report_simple


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    repo_root = os.getenv("FT_REPO_ROOT", ".")
    out_json = os.getenv("FT_AUDIT_JSON", ".firsttry/audit.json")
    out_txt = os.getenv("FT_AUDIT_SUMMARY", ".firsttry/audit_summary.txt")
    notes = os.getenv("FT_AUDIT_NOTES", "audit workflow")

    # Policy inputs
    policy_url = os.getenv("FT_POLICY_URL") or os.getenv("POLICY_URL")
    policy_hash = os.getenv("FT_POLICY_HASH") or os.getenv("POLICY_HASH")

    # If only URL is provided and it's file://, compute hash now
    if policy_url and not policy_hash and policy_url.startswith("file://"):
        p = Path(policy_url.removeprefix("file://"))
        if not p.exists():
            print(f"[emit] policy file not found: {p}", file=sys.stderr)
            return 2
        policy_hash = "sha256:" + sha256_of(p)

    # Minimal required emitter fields — adjust if yours differ
    overall_score = int(os.getenv("FT_OVERALL_SCORE", "92"))
    category_scores = json.loads(os.getenv("FT_CATEGORY_SCORES", '{"security":98}'))
    gates_executed = json.loads(os.getenv("FT_GATES_EXECUTED", "[]"))
    repository = json.loads(
        os.getenv("FT_REPOSITORY", '{"owner":"local","name":"Firstry","url":""}')
    )
    branch = os.getenv("FT_BRANCH", "local")
    commit_info = json.loads(
        os.getenv("FT_COMMIT_INFO", '{"sha":"local","author":"actor","message":""}')
    )
    tier = os.getenv("FT_TIER", "pro")

    emit_audit_report_simple(
        repo_root=repo_root,
        policy_url=policy_url,
        policy_hash=policy_hash,
        notes=notes,
        out_json=out_json,
        out_txt=out_txt,
        overall_score=overall_score,
        category_scores=category_scores,
        gates_executed=gates_executed,
        repository=repository,
        branch=branch,
        commit_info=commit_info,
        tier=tier,
    )
    print(f"[emit] wrote {out_json} and {out_txt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
