from pathlib import Path
import re

ALLOWLIST = {
    "tests/test_config_compat.py",
    # allow the tooling package to define its own FirstTryConfig
    "tools/firsttry/firsttry/config.py",
    # allow the alias in the main src config and allow this guard test itself
    "src/firsttry/config.py",
    "tests/test_no_alias_in_repo.py",
}

def test_no_global_alias_usage() -> None:
    root = Path(__file__).resolve().parents[1]
    offenders = []
    for p in root.rglob("*.py"):
        rel = p.relative_to(root).as_posix()
        if rel in ALLOWLIST:
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"\bFirstTryConfig\b", txt):
            offenders.append(rel)
    assert not offenders, f"FirstTryConfig alias used in: {offenders}"
