from pathlib import Path
import argparse

from .runner_light import run_profile


def main() -> int:
    p = argparse.ArgumentParser("firsttry-lite")
    p.add_argument("--profile", default="fast", choices=["fast", "strict", "release"])
    p.add_argument("--since", default=None, help="git ref, e.g. HEAD~1")
    args = p.parse_args()
    return run_profile(Path("."), args.profile, args.since)


if __name__ == "__main__":
    raise SystemExit(main())
