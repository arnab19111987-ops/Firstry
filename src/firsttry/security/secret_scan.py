from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass
class SecretFinding:
    path: str
    line: int
    pattern: str
    snippet: str


COMMON_EXT = {".py", ".js", ".ts", ".env", ".yaml", ".yml", ".json", ".ini", ".toml"}

# Simple regexes for known patterns
PATTERNS = {
    "AWS_SECRET_ACCESS_KEY": re.compile(r"AKIA[0-9A-Z]{16}"),
    "AWS_ACCESS_KEY_ID": re.compile(r"(?i)aws_access_key_id\s*[:=]\s*[A-Za-z0-9/+=]+"),
    "stripe_sk_live": re.compile(r"sk_live_[0-9a-zA-Z]{24,}"),
    "github_pat": re.compile(r"ghp_[0-9A-Za-z_]{36,}"),
    "slack_xoxb": re.compile(r"xoxb-[0-9A-Za-z-]+"),
}

# High-entropy token-ish pattern (base64-like) — long strings of [A-Za-z0-9+/=]{40,}
ENTROPY_RE = re.compile(r"[A-Za-z0-9+/=]{40,}")


def _is_text_file(path: Path) -> bool:
    try:
        _ = path.read_text(encoding="utf-8")
        return True
    except Exception:
        return False


def scan_text_for_secrets(text: str) -> List[str]:
    hits: List[str] = []
    for name, rx in PATTERNS.items():
        if rx.search(text):
            hits.append(name)
    # entropy quick check
    if ENTROPY_RE.search(text):
        hits.append("high_entropy")
    return hits


def scan_files(paths: Iterable[str]) -> List[SecretFinding]:
    findings: List[SecretFinding] = []
    for p in paths:
        path = Path(p)
        if not path.exists() or path.is_dir():
            continue
        if path.suffix and path.suffix.lower() not in COMMON_EXT:
            continue
        if not _is_text_file(path):
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for i, L in enumerate(text.splitlines(), start=1):
            for name, rx in PATTERNS.items():
                m = rx.search(L)
                if m:
                    snippet = m.group(0)
                    masked = snippet[:8] + "*" * max(4, len(snippet) - 12) + snippet[-4:]
                    findings.append(SecretFinding(str(path), i, name, masked))
            # entropy check
            me = ENTROPY_RE.search(L)
            if me and len(me.group(0)) >= 48:
                token = me.group(0)
                masked = token[:8] + "*" * (len(token) - 12) + token[-4:]
                findings.append(SecretFinding(str(path), i, "high_entropy", masked))

    return findings


def scan_changed_files(changed_files: Iterable[str]) -> List[SecretFinding]:
    if not changed_files:
        return []
    if "**" in changed_files:
        files = [
            str(p) for p in Path(".").rglob("*") if p.is_file() and p.suffix.lower() in COMMON_EXT
        ]
        return scan_files(files)
    return scan_files(changed_files)


__all__ = ["SecretFinding", "scan_files", "scan_changed_files", "scan_text_for_secrets"]
