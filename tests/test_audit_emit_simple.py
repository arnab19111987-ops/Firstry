import json
from pathlib import Path

from tools.audit_emit import emit_audit_report_simple


def test_emit_simple_includes_policy(tmp_path: Path):
    pol = tmp_path / ".firsttry" / "policy.txt"
    pol.parent.mkdir(parents=True, exist_ok=True)
    pol.write_text("strict=1\n")
    h = "deadbeef" * 8

    emit_audit_report_simple(
        repo_root=tmp_path.as_posix(),
        policy_url=f"file://{pol.as_posix()}",
        policy_hash=h,
        notes="test",
        out_json=str(tmp_path / ".firsttry" / "audit.json"),
        out_txt=None,
        # minimal fields the core emitter expects; adjust if yours differ
        overall_score=90,
        category_scores={"security": 95},
        gates_executed=[],
        repository={"owner": "o", "name": "n", "url": ""},
        branch="b",
        commit_info={"sha": "s", "author": "a", "message": ""},
        tier="pro",
    )

    j = json.load(open(tmp_path / ".firsttry" / "audit.json"))
    c = j["compliance"]
    assert c["policy_enforced"] is True
    assert c["policy_url"].endswith("/policy.txt")
    assert c["policy_hash"] == h
