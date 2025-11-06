from firsttry.mapper import guess_test_kexpr


def test_guess_expr_from_changed():
    expr = guess_test_kexpr(
        ["tools/firsttry/firsttry/cli.py", "tools/firsttry/tests/test_config.py"],
    )
    assert "cli" in expr and "config" in expr
