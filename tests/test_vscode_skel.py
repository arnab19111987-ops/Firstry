import json
from firsttry.vscode_skel import PACKAGE_JSON, EXTENSION_JS


def test_package_json_is_valid_and_command_defined():
    data = json.loads(PACKAGE_JSON)
    assert data["main"] == "./extension.js"
    assert data["contributes"]["commands"][0]["command"] == "firsttry.runGate"
    assert "Run Gate" in data["contributes"]["commands"][0]["title"]


def test_extension_js_mentions_python_module():
    # crude sanity check
    assert "python -m firsttry run" in EXTENSION_JS
    assert "firsttry.runGate" in EXTENSION_JS
