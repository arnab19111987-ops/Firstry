from firsttry.runners.pytest import build_pytest_cmd


def test_no_k_in_cmd_for_nodeids():
    cmd = build_pytest_cmd(["a::b", "c::d"], extra=[])
    s = " ".join(cmd)
    assert " -k " not in s
    assert "a::b" in s and "c::d" in s
