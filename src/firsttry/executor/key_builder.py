from __future__ import annotations

from pathlib import Path

from ..twin.hashers import env_fingerprint, hash_bytes, hash_file, tool_version_hash


def build_cache_key(repo_root: Path, cmd: list[str], inputs: set[str]) -> str:
    """Inputs can contain:
    - repo-relative file paths ("src/app/x.py")
    - special tokens: "TOOL:ruff", "TOOL:mypy", "CONF:pyproject.toml"
    """
    file_hashes: list[str] = []
    tokens: list[str] = []
    for item in sorted(inputs):
        if item.startswith("TOOL:"):
            tool = item.split(":", 1)[1]
            # simple: "<tool> --version"
            tokens.append(f"TV:{tool}:{tool_version_hash([tool, '--version'])}")
        elif item.startswith("CONF:"):
            rel = item.split(":", 1)[1]
            p = repo_root / rel
            if p.exists():
                file_hashes.append(f"C:{rel}:{hash_file(p)}")
        else:
            p = repo_root / item
            if p.exists() and p.is_file():
                file_hashes.append(f"F:{item}:{hash_file(p)}")

    env = env_fingerprint()
    cmd_sig = " ".join(cmd).encode()
    key_data = "::".join(
        sorted(file_hashes) + sorted(tokens) + [env, "CMD:" + hash_bytes(cmd_sig)],
    )
    return "ft-v1-" + hash_bytes(key_data.encode())
