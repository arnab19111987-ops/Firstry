import importlib
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def safe_isolated_env(monkeypatch, tmp_path):
    """
    Isolates every test from its *environment* to prevent state pollution.
    This runs automatically for every test.

    This SAFE version:
      - Clears known FirstTry environment variables.
      - Reloads stateful modules (like license/config) to clear caches.
      * Does NOT change the current working directory (which broke everything).
      - DOES sandbox the *home directory* to prevent global config-file-bleed.
    """

    # 1. Isolate Environment Variables
    vars_to_clear = [
        "FIRSTTRY_LICENSE_KEY",
        "FIRSTTRY_LICENSE_URL",
        "FIRSTTRY_LICENSE_ALLOW",
        "FIRSTTRY_ALLOW_UNLICENSED",
        "FIRSTTRY_FORCE_TIER",
        "FIRSTTRY_DEMO_MODE",
        "FIRSTTRY_SEND_TELEMETRY",
        "FIRSTTRY_TELEMETRY_OPTOUT",
        "FT_S3_BUCKET",
        "FT_S3_PREFIX",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_REGION",
    ]
    for var in vars_to_clear:
        monkeypatch.delenv(var, raising=False)

    # 2. Isolate Module Caches (by reloading them)
    mods_to_reload = [
        "firsttry.license_guard",
        "firsttry.license_cache",
        "firsttry.config.schema",
    ]
    for mod_name in mods_to_reload:
        if mod_name in importlib.sys.modules:
            try:
                importlib.reload(importlib.import_module(mod_name))
            except ImportError:
                pass  # Module might not exist in all test contexts

    # 3. Isolate Filesystem Config (The SAFER way)
    # We point the "home" dir to a temp folder so no global
    # ~/.config/firsttry/config.toml is ever found.
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    yield  # <--- THE TEST RUNS HERE
