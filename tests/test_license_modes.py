from firsttry.config.schema import AppCfg
from firsttry.config.schema import LicenseCfg
from firsttry.license_guard import resolve_license


def test_offline_license_grace(tmp_path, monkeypatch):
    f = tmp_path/"license.toml"
    f.write_text('tier="pro"\nexpires_at=0\n')
    cfg = AppCfg(license=LicenseCfg(mode="offline", file=str(f), grace_days=0))
    lic = resolve_license(cfg)
    assert lic.tier == "pro" and lic.verified
