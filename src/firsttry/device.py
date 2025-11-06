import json
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from pathlib import Path

DEVICE_DIR = Path.home() / ".firsttry"
DEVICE_FILE = DEVICE_DIR / "device.json"
FREEMIUM_DAYS = 25


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _ensure_dir():
    DEVICE_DIR.mkdir(parents=True, exist_ok=True)


def load_device():
    _ensure_dir()
    if not DEVICE_FILE.exists():
        return None
    try:
        return json.loads(DEVICE_FILE.read_text())
    except Exception:
        return None


def save_device(d):
    _ensure_dir()
    DEVICE_FILE.write_text(json.dumps(d, indent=2))


def create_device():
    d = {
        "device_id": str(uuid.uuid4()),
        "created_at": _now_iso(),
        "last_seen_at": _now_iso(),
        "level2_consumed": False,
        "level3_consumed": False,
        "freemium_started_at": _now_iso(),
        "license_key": None,
        "license_activated_at": None,
    }
    save_device(d)
    return d


def touch_device():
    d = load_device() or create_device()
    d["last_seen_at"] = _now_iso()
    save_device(d)
    return d


def mark_consumed(level):
    d = load_device() or create_device()
    if level == 2:
        d["level2_consumed"] = True
    elif level == 3:
        d["level3_consumed"] = True
    save_device(d)
    return d


def set_license(key):
    d = load_device() or create_device()
    # prefer to store only an obfuscated token in future; store raw for now
    d["license_key"] = key
    d["license_activated_at"] = _now_iso()
    save_device(d)
    return d


def freemium_expired():
    d = load_device() or create_device()
    try:
        start = datetime.fromisoformat(d["freemium_started_at"])
    except Exception:
        # if parsing fails, treat as not expired
        return False
    return (datetime.now(timezone.utc) - start) >= timedelta(days=FREEMIUM_DAYS)
