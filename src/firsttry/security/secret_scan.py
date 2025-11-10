from __future__ import annotations

import re
from typing import Iterable, List


SIMPLE_SECRET_PATTERNS = [
    re.compile(r"(?i)password\s*[:=]\s*\S+"),
    re.compile(r"(?i)secret\s*[:=]\s*\S+"),
    re.compile(r"ghp_[A-Za-z0-9_]+"),
]


def scan_text_for_secrets(text: str) -> List[str]:
    findings: List[str] = []
    for p in SIMPLE_SECRET_PATTERNS:
        if p.search(text):
            findings.append(p.pattern)
    return findings


def scan_changed_files(changed_files: Iterable[str], repo_root: str = ".") -> List[str]:
    hits: List[str] = []
    for path in changed_files:
        try:
            with open(path, "r", errors="ignore") as f:
                txt = f.read()
        except Exception:
            continue
        fns = scan_text_for_secrets(txt)
        if fns:
            hits.append(path)
    return hits


__all__ = ["scan_changed_files"]
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List


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
        # Quick heuristic
        s = path.read_text(encoding="utf-8")
        return True
    except Exception:
        return False


def scan_files(paths: List[str]) -> List[SecretFinding]:
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
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue

        for i, L in enumerate(lines, start=1):
            for name, rx in PATTERNS.items():
                if rx.search(L):
                    snippet = rx.search(L).group(0)
                    masked = snippet[:8] + "*" * max(4, len(snippet) - 12) + snippet[-4:]
                    findings.append(SecretFinding(str(path), i, name, masked))
            # entropy check
            if ENTROPY_RE.search(L):
                token = ENTROPY_RE.search(L).group(0)
                if len(token) >= 48:
                    masked = token[:8] + "*" * (len(token) - 12) + token[-4:]
                    findings.append(SecretFinding(str(path), i, "high_entropy", masked))

    return findings


def scan_changed_files(changed_files: List[str]) -> List[SecretFinding]:
    # changed_files may include '**' meaning all files; in that case scan repo
    if not changed_files:
        return []
    if "**" in changed_files:
        # scan all files in repo root matching extensions
        files = [str(p) for p in Path('.').rglob('*') if p.is_file() and p.suffix.lower() in COMMON_EXT]
        return scan_files(files)
    return scan_files(changed_files)


__all__ = ["SecretFinding", "scan_files", "scan_changed_files"]
