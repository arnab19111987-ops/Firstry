# src/firsttry/license_trial.py
import json
import time
from pathlib import Path

TRIAL_FILE = Path.home() / ".firsttry" / "license_trial.json"

TRIAL_DAYS = 3
GRACE_RUNS = 6


def _now() -> float:
    return time.time()


def load_trial():
    if not TRIAL_FILE.exists():
        return None
    try:
        return json.loads(TRIAL_FILE.read_text())
    except Exception:
        return None


def save_trial(data: dict):
    TRIAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    TRIAL_FILE.write_text(json.dumps(data))


def init_trial(license_key: str):
    now = _now()
    data = {
        "license_key": license_key,
        "started": now,
        "expires": now + TRIAL_DAYS * 24 * 3600,
        "runs_after_expiry": 0,
        "max_runs_after_expiry": GRACE_RUNS,
    }
    save_trial(data)
    return data


def trial_status():
    data = load_trial()
    if not data:
        return "no_trial", None

    now = _now()
    if now < data["expires"]:
        remaining_seconds = data["expires"] - now
        days_left = int(remaining_seconds // 86400)
        return "trial_active", days_left

    # expired, check grace
    if data["runs_after_expiry"] < data["max_runs_after_expiry"]:
        left = data["max_runs_after_expiry"] - data["runs_after_expiry"]
        data["runs_after_expiry"] += 1
        save_trial(data)
        return "grace_active", left

    return "expired", 0