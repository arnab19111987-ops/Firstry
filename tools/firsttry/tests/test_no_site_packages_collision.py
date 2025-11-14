import firsttry as pkg


def test_not_from_site_packages():
    # Fail if the tooling suite resolved an installed package from site-packages
    assert "site-packages" not in (pkg.__file__ or ""), (
        "Tooling suite resolved installed repo package"
    )
