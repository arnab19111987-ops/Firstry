from __future__ import annotations

import time
import urllib.request
import urllib.error
from typing import Tuple


def build_compose_cmds(compose_file: str = "docker-compose.yml") -> Tuple[str, str]:
    """
    Return the docker compose 'up' and 'down' commands we would run
    as plain shell strings.
    """
    up_cmd = f"docker compose -f {compose_file} up -d"
    down_cmd = f"docker compose -f {compose_file} down"
    return up_cmd, down_cmd


def _http_ok(url: str, timeout: float) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return False


def check_health(
    url: str = "http://localhost:8000/healthz", timeout: float = 5.0
) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _http_ok(url, timeout=timeout):
            return True
        time.sleep(0.05)
    return False


def run_docker_smoke() -> None:
    up_cmd, down_cmd = build_compose_cmds()
    print(f"Docker smoke plan: {up_cmd} ; {down_cmd}")

    healthy = check_health()
    if not healthy:
        raise RuntimeError("Container stack did not become healthy.")

    print("Docker smoke OK (stack healthy).")
