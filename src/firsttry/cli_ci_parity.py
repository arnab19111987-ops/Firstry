from __future__ import annotations

from argparse import ArgumentParser
from .ci_parity import runner as ci_runner


def main(argv: list[str] | None = None) -> int:
    parser = ArgumentParser(prog="ft ci-parity")
    parser.add_argument(
        "profile",
        choices=["pre-commit", "pre-push", "commit", "push", "ci"],
    )
    args = parser.parse_args(argv)
    return ci_runner.main([args.profile])


if __name__ == "__main__":
    raise SystemExit(main())
