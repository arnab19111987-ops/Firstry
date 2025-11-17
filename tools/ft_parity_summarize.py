#!/usr/bin/env python
import json
from pathlib import Path

LOG_PATH = Path(".firsttry/parity/pytest_parity_latest.log")
OUT_PATH = Path(".firsttry/parity/pytest_parity_summary.json")


def main() -> None:
    if not LOG_PATH.exists():
        raise SystemExit(f"Log not found: {LOG_PATH}")

    text = LOG_PATH.read_text(errors="replace")
    lines = text.splitlines()

    failed = []
    for line in lines:
        if line.startswith("FAILED "):
            try:
                part = line.split("FAILED ", 1)[1]
            except IndexError:
                continue
            test_id, _, message = part.partition(" - ")
            failed.append({"test": test_id.strip(), "message": message.strip()})

    summary_line = None
    # find pytest summary line with failed/passed/warnings
    for line in reversed(lines):
        line_str = line.strip()
        if ("failed" in line_str or "passed" in line_str) and (
            "=" in line_str or "====" in line_str
        ):
            summary_line = line_str
        break

    result = {
        "status": "failed" if failed else "passed",
        "failed_tests": failed,
        "pytest_summary": summary_line,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
