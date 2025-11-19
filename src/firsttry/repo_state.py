import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def repo_root_cwd(cwd):
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], cwd=cwd, stderr=subprocess.DEVNULL
        )
        return out.decode().strip()
    except Exception:
        return None


def repo_id_from_root(root):
    # prefer remote URL if exists
    try:
        remote = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=root,
            stderr=subprocess.DEVNULL,
        )
        remote = remote.decode().strip()
    except Exception:
        remote = root
    key = (root + "::" + remote).encode()
    return hashlib.sha1(key).hexdigest()


def state_file_for_repo(root):
    p = Path(root) / ".firsttry"
    p.mkdir(parents=True, exist_ok=True)
    return p / "state.json"


def load_repo_state(cwd):
    root = repo_root_cwd(cwd)
    if not root:
        return None
    sf = state_file_for_repo(root)
    try:
        return json.loads(sf.read_text())
    except Exception:
        return None


def create_or_touch_repo_state(cwd):
    root = repo_root_cwd(cwd)
    if not root:
        return None
    sf = state_file_for_repo(root)
    if sf.exists():
        try:
            s = json.loads(sf.read_text())
            s["last_seen_at"] = datetime.now(timezone.utc).isoformat()
            sf.write_text(json.dumps(s, indent=2))
            return s
        except Exception:
            pass
    s = {
        "repo_id": repo_id_from_root(root),
        "first_used_at": datetime.now(timezone.utc).isoformat(),
        "level2_consumed": False,
        "level3_consumed": False,
    }
    sf.write_text(json.dumps(s, indent=2))
    return s


def mark_repo_consumed(cwd, level):
    st = create_or_touch_repo_state(cwd)
    if not st:
        return None
    if level == 2:
        st["level2_consumed"] = True
    elif level == 3:
        st["level3_consumed"] = True
    sf = state_file_for_repo(repo_root_cwd(cwd))
    sf.write_text(json.dumps(st, indent=2))
    return st
