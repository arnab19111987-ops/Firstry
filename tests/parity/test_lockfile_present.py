from pathlib import Path


def test_parity_lock_present():
    assert Path('.firsttry/parity.lock.json').is_file()
