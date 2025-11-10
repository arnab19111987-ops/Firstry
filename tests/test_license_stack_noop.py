"""
Smoke: importing the licensing stack shouldn’t explode when network/boto3 are stubbed.
"""

import importlib


def test_license_modules_import():
    importlib.import_module("firsttry.license")
    importlib.import_module("firsttry.license_cache")
    importlib.import_module("firsttry.license_fast")
    importlib.import_module("firsttry.license_guard")
    importlib.import_module("firsttry.license_trial")
    importlib.import_module("firsttry.licensing")
