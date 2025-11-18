import os
import sys

from .device import freemium_expired, mark_consumed, set_license, touch_device
from .repo_state import create_or_touch_repo_state, mark_repo_consumed

TRIAL_URL = "https://www.firsttry.run/trial"


def is_unlicensed_env():
    if os.getenv("FIRSTTRY_ALLOW_UNLICENSED") == "1":
        return True
    return "--silent-unlicensed" in " ".join(sys.argv)


def require_license_prompt():
    print()
    print("🔒 FirstTry advanced checks require a trial or paid license.")
    print(f"Get a trial at: {TRIAL_URL}")
    key = input("Enter license / trial key (required): ").strip()
    if not key:
        print("❌ No license entered. Exiting.")
        raise SystemExit(3)
    # store locally (you can verify with server later)
    set_license(key)
    print("✅ License stored locally. Continuing...")


def allow_or_block_for_level(level, cwd):
    # level is int 1..4
    if level <= 1:
        touch_device()
        create_or_touch_repo_state(cwd)
        return True  # always allowed

    if is_unlicensed_env():
        return True

    # device & repo states
    dev = touch_device()
    repo = create_or_touch_repo_state(cwd)

    # Determine whether both levels have been consumed at least once
    dev_consumed_2 = bool(dev.get("level2_consumed"))
    dev_consumed_3 = bool(dev.get("level3_consumed"))
    repo_consumed_2 = bool(repo.get("level2_consumed")) if repo else False
    repo_consumed_3 = bool(repo.get("level3_consumed")) if repo else False

    consumed2 = dev_consumed_2 or repo_consumed_2
    consumed3 = dev_consumed_3 or repo_consumed_3

    # strict version inside allow_or_block_for_level
    if level >= 2:
        if freemium_expired() or (consumed2 and consumed3):
            require_license_prompt()
            return True
        # first ever L2
        if level == 2 and not consumed2:
            mark_consumed(2)
            mark_repo_consumed(cwd, 2)
            return True
        # first ever L3
        if level == 3 and not consumed3:
            mark_consumed(3)
            mark_repo_consumed(cwd, 3)
            return True
        # everything else (i.e. second L2, second L3, L4 before both tasted)
        require_license_prompt()
        return True

    return True
