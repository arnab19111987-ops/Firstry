from pathlib import Path


def test_no_config_file_shadow():
    assert not Path("src/firsttry/config.py").exists(), (
        "Move src/firsttry/config.py into src/firsttry/config/ package (shadowing breaks submodule imports)."
    )
