#!/usr/bin/env python3
import json
import subprocess
import sys
import time
from typing import List


def main(argv: List[str]) -> int:
    if not argv:
        print(json.dumps({"error":"no command provided"}))
        return 2
    cmd = argv
    t0 = time.perf_counter()
    try:
        cp = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=600
        )
        dur = (time.perf_counter() - t0) * 1000.0
        out_tail = (cp.stdout or "")[-4000:]
        err_tail = (cp.stderr or "")[-4000:]
        traceback = ("Traceback (most recent call last):" in err_tail) or ("Traceback (most recent call last):" in out_tail)
        rec = {
            "cmd": cmd,
            "exit_code": cp.returncode,
            "duration_ms": round(dur, 2),
            "stdout_tail": out_tail,
            "stderr_tail": err_tail,
            "has_traceback": bool(traceback),
            "ts": int(time.time()),
        }
        print(json.dumps(rec, ensure_ascii=False))
        return 0
    except subprocess.TimeoutExpired as e:
        dur = (time.perf_counter() - t0) * 1000.0
        rec = {
            "cmd": cmd,
            "exit_code": 124,
            "duration_ms": round(dur, 2),
            "stdout_tail": (e.stdout or "")[-4000:] if hasattr(e, "stdout") else "",
            "stderr_tail": (e.stderr or "")[-4000:] if hasattr(e, "stderr") else "",
            "has_traceback": False,
            "timeout": True,
            "ts": int(time.time()),
        }
        print(json.dumps(rec, ensure_ascii=False))
        return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
