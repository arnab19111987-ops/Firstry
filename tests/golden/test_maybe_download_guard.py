from firsttry.ci_parity.cache_utils import maybe_download_golden_cache


def test_noop_without_env(monkeypatch):
    monkeypatch.delenv("FT_S3_BUCKET", raising=False)
    monkeypatch.delenv("FT_S3_PREFIX", raising=False)
    # should not raise
    maybe_download_golden_cache()
