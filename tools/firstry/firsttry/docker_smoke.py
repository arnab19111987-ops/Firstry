"""
Day 7 docker smoke:
- Build commands for `docker compose up -d`
- Check /healthz
- Tear down with `docker compose down`

We keep network interaction & docker calls separate so tests can verify logic
without actually needing docker.

Public API:
    build_compose_cmds(compose_file="docker-compose.yml") -> (up_cmd, down_cmd)
    check_health(url="http://localhost:8000/healthz", timeout=5.0) -> bool
    run_docker_smoke(compose_file, health_url, timeout=5.0) -> dict
"""

from __future__ import annotations

import subprocess
import time
import urllib.request
from typing import Tuple


def build_compose_cmds(compose_file: str = "docker-compose.yml") -> Tuple[str, str]:
    up_cmd = f"docker compose -f {compose_file} up -d"
    down_cmd = f"docker compose -f {compose_file} down"
    return up_cmd, down_cmd


def check_health(
    url: str = "http://localhost:8000/healthz", timeout: float = 5.0
) -> bool:
    """
    Returns True if GET <url> returns HTTP 200 within timeout seconds.
    Simple polling loop.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if 200 <= resp.status < 300:
                    return True
        except Exception:
            # service not up yet or bad path
            time.sleep(0.25)
            continue
    return False


def run_docker_smoke(
    compose_file: str = "docker-compose.yml",
    health_url: str = "http://localhost:8000/healthz",
    timeout: float = 5.0,
) -> dict:
    """
    Full flow:
    - docker compose up -d
    - poll /healthz
    - docker compose down
    Returns:
    {
      "up_ok": bool,
      "health_ok": bool,
      "down_ok": bool,
      "error": str|None,
    }
    """
    up_cmd, down_cmd = build_compose_cmds(compose_file)

    def _run(cmd: str) -> bool:
        p = subprocess.run(cmd, shell=True)
        return p.returncode == 0

    up_ok = _run(up_cmd)
    if not up_ok:
        # attempt teardown anyway
        _run(down_cmd)
        return {
            "up_ok": False,
            "health_ok": False,
            "down_ok": True,
            "error": f"Failed to bring up stack with '{up_cmd}'",
        }

    health_ok = check_health(url=health_url, timeout=timeout)

    down_ok = _run(down_cmd)

    return {
        "up_ok": up_ok,
        "health_ok": health_ok,
        "down_ok": down_ok,
        "error": (
            None if (up_ok and health_ok and down_ok) else "Health or teardown failed"
        ),
    }
